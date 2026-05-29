import json

import yaml

from beacon.runtime_snapshot import analyze_runtime_snapshot


def analyze_opentelemetry_file(path):
    snapshot, collection_findings = collect_opentelemetry_snapshot(path)
    findings = list(collection_findings)

    if snapshot:
        findings.extend(analyze_runtime_snapshot(snapshot, source=path))

    return findings


def collect_opentelemetry_snapshot(path):
    with open(path, "r") as f:
        data = load_telemetry(f, path)

    telemetry = data.get("opentelemetry", data)
    spans = telemetry.get("spans", []) or []
    metrics = telemetry.get("metrics", []) or []
    flow = telemetry.get("flow", {}) or {}

    findings = [
        opentelemetry_finding(
            "opentelemetry.runtime.read_only_mode",
            "INFO",
            "Beacon OpenTelemetry connector is running in read-only diagnostic mode",
            "Beacon will only read exported OpenTelemetry spans and metrics.",
            "No workload or telemetry backend mutation operation will be performed.",
            path,
            {"mode": "read_only", "mutation_allowed": False},
        )
    ]

    snapshot = {}

    api_services = build_api_runtime(spans)
    if api_services:
        snapshot["api_runtime"] = {"services": api_services}

    databases = build_database_runtime(spans, metrics)
    if databases:
        snapshot["database_runtime"] = {"databases": databases}

    storage_resources = build_storage_runtime(metrics)
    if storage_resources:
        snapshot["storage_runtime"] = {"resources": storage_resources}

    flow_runtime = build_flow_runtime(flow, spans, metrics)
    if flow_runtime:
        snapshot["flow_runtime"] = flow_runtime

    if not snapshot:
        findings.append(
            opentelemetry_finding(
                "opentelemetry.runtime.signals.missing",
                "ERROR",
                "OpenTelemetry input did not contain usable runtime signals",
                "Beacon could not derive API, database, storage, or flow runtime resources from the provided telemetry.",
                "Provide spans or metrics with service names, durations, status, and relevant runtime signal values.",
                path,
                {"spans": len(spans), "metrics": len(metrics)},
            )
        )

    return snapshot, findings


def load_telemetry(file_obj, path):
    if path.endswith(".json"):
        return json.load(file_obj) or {}

    return yaml.safe_load(file_obj) or {}


def build_api_runtime(spans):
    by_service = {}

    for span in spans:
        service = span.get("service") or span.get("service_name")
        if not service:
            continue

        by_service.setdefault(service, []).append(span)

    services = []

    for service, service_spans in by_service.items():
        durations = [span_duration_ms(span) for span in service_spans]
        durations = [duration for duration in durations if duration is not None]

        if not durations:
            continue

        total = len(service_spans)
        errors = [span for span in service_spans if span_is_error(span)]
        timeouts = [span for span in service_spans if span_is_timeout(span)]
        retries = [span for span in service_spans if span_is_retry(span)]

        services.append(
            {
                "name": service,
                "latency_p95_ms": percentile(durations, 95),
                "error_rate_percent": percent(len(errors), total),
                "timeout_rate_percent": percent(len(timeouts), total),
                "retry_rate_percent": percent(len(retries), total),
                "recent_deployment": any(span_recent_deployment(span) for span in service_spans),
            }
        )

    return services


def build_database_runtime(spans, metrics):
    database_spans = [span for span in spans if span_is_database(span)]
    databases = {}

    for span in database_spans:
        name = span_database_name(span)
        databases.setdefault(
            name,
            {
                "name": name,
                "engine": span_attributes(span).get("db.system"),
                "_durations": [],
            },
        )
        duration = span_duration_ms(span)
        if duration is not None:
            databases[name]["_durations"].append(duration)

    for metric in metrics:
        name = metric.get("database") or metric.get("target") or metric.get("resource")
        if not name:
            continue

        metric_name = metric.get("name")
        value = metric.get("value")
        database = databases.setdefault(name, {"name": name, "_durations": []})

        if metric_name == "database.connection_pool_utilization_percent":
            database["connection_pool_utilization_percent"] = value
        elif metric_name == "database.replication_lag_seconds":
            database["replication_lag_seconds"] = value
        elif metric_name == "database.lock_waits_high":
            database["lock_waits_high"] = bool(value)
        elif metric_name == "database.storage_used_percent":
            database["storage_used_percent"] = value
        elif metric_name == "database.latency_ms":
            database["latency_ms"] = value

    output = []
    for database in databases.values():
        durations = database.pop("_durations", [])
        if durations and "latency_ms" not in database:
            database["latency_ms"] = percentile(durations, 95)
        output.append(database)

    return output


def build_storage_runtime(metrics):
    resources = {}

    for metric in metrics:
        name = metric.get("resource") or metric.get("target")
        if not name:
            continue

        metric_name = metric.get("name")
        value = metric.get("value")
        resource = resources.setdefault(
            name,
            {
                "name": name,
                "type": metric.get("type", "storage"),
            },
        )

        if metric_name == "storage.used_percent":
            resource["used_percent"] = value
        elif metric_name == "storage.growth_percent_7d":
            resource["growth_percent_7d"] = value
        elif metric_name == "storage.iops_saturation_percent":
            resource["iops_saturation_percent"] = value
        elif metric_name == "storage.backup_age_hours":
            resource["backup_age_hours"] = value

    return list(resources.values())


def build_flow_runtime(flow, spans, metrics):
    flow_name = flow.get("name")
    if not flow_name:
        return {}

    signals = dict(flow.get("signals", {}))
    api_services = build_api_runtime(spans)
    databases = build_database_runtime(spans, metrics)

    if api_services:
        signals.setdefault(
            "api_timeout_rate_percent",
            max(service.get("timeout_rate_percent", 0) for service in api_services),
        )
        signals.setdefault(
            "api_error_rate_percent",
            max(service.get("error_rate_percent", 0) for service in api_services),
        )
        signals.setdefault(
            "latency_p95_ms",
            max(service.get("latency_p95_ms", 0) for service in api_services),
        )

    if databases:
        signals.setdefault(
            "db_latency_ms",
            max(database.get("latency_ms", 0) for database in databases),
        )

    for metric in metrics:
        metric_name = metric.get("name")
        value = metric.get("value")

        if metric_name == "kafka.consumer_lag_increasing":
            signals["kafka_consumer_lag_increasing"] = bool(value)
        elif metric_name == "kafka.broker_unhealthy":
            signals["kafka_broker_unhealthy"] = bool(value)
        elif metric_name == "consumer.retry_rate_percent":
            signals["consumer_retry_rate_percent"] = value
        elif metric_name == "deployment.recent":
            signals["recent_deployment"] = bool(value)
        elif metric_name == "api.error_rate_percent":
            signals["api_error_rate_percent"] = value

    return {
        "name": flow_name,
        "signals": signals,
        "components": flow.get("components", {}),
    }


def span_duration_ms(span):
    if span.get("duration_ms") is not None:
        return span.get("duration_ms")

    start = span.get("start_time_unix_nano")
    end = span.get("end_time_unix_nano")

    if start is not None and end is not None:
        return (end - start) / 1_000_000

    return None


def span_attributes(span):
    return span.get("attributes", {}) or {}


def span_is_error(span):
    status = str(span.get("status", "")).upper()
    attributes = span_attributes(span)
    status_code = attributes.get("http.status_code")

    if isinstance(status_code, str) and status_code.isdigit():
        status_code = int(status_code)

    return status in {"ERROR", "STATUS_CODE_ERROR"} or (
        isinstance(status_code, int) and status_code >= 500
    )


def span_is_timeout(span):
    attributes = span_attributes(span)
    error_type = str(attributes.get("error.type", "")).lower()
    status = str(span.get("status", "")).lower()

    return "timeout" in error_type or "timeout" in status


def span_is_retry(span):
    attributes = span_attributes(span)

    return bool(attributes.get("retry") or attributes.get("retry.count", 0))


def span_recent_deployment(span):
    attributes = span_attributes(span)

    return bool(attributes.get("deployment.recent"))


def span_is_database(span):
    attributes = span_attributes(span)

    return bool(attributes.get("db.system") or attributes.get("db.name"))


def span_database_name(span):
    attributes = span_attributes(span)

    return attributes.get("db.name") or attributes.get("database") or "unknown-database"


def percentile(values, percent_value):
    if not values:
        return None

    ordered = sorted(values)
    index = round((len(ordered) - 1) * (percent_value / 100))

    return ordered[index]


def percent(count, total):
    if total == 0:
        return 0

    return (count / total) * 100


def opentelemetry_finding(rule_id, severity, title, impact, recommendation, file, evidence):
    return {
        "rule_id": rule_id,
        "domain": "opentelemetry",
        "category": "runtime_stability",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence,
        "tags": ["opentelemetry", "runtime", "collector"],
    }
