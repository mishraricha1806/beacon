import json
import logging
import time

import yaml

from beacon.input_validation import missing_path_finding, path_missing
from beacon.runtime_snapshot import analyze_runtime_snapshot

LOGGER = logging.getLogger(__name__)


def analyze_opentelemetry_file(path):
    started = time.monotonic()
    LOGGER.info("opentelemetry.start path=%s", path)
    snapshot, collection_findings = collect_opentelemetry_snapshot(path)
    findings = list(collection_findings)

    if snapshot:
        LOGGER.info(
            "opentelemetry.snapshot_analyze path=%s sections=%s",
            path,
            sorted(snapshot.keys()),
        )
        findings.extend(analyze_runtime_snapshot(snapshot, source=path))

    LOGGER.info(
        "opentelemetry.complete path=%s findings=%s elapsed=%.2fs",
        path,
        len(findings),
        time.monotonic() - started,
    )
    return findings


def collect_opentelemetry_snapshot(path):
    LOGGER.info("opentelemetry.load path=%s", path)
    if path_missing(path):
        LOGGER.warning("opentelemetry.path_missing path=%s", path)
        return {}, [missing_path_finding(path)]

    with open(path, "r") as f:
        data = load_telemetry(f, path)

    telemetry = data.get("opentelemetry", data)
    spans = telemetry.get("spans", []) or []
    metrics = telemetry.get("metrics", []) or []
    flow = telemetry.get("flow", {}) or {}
    LOGGER.info(
        "opentelemetry.loaded path=%s spans=%s metrics=%s flow=%s",
        path,
        len(spans),
        len(metrics),
        bool(flow),
    )

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
    LOGGER.info("opentelemetry.api_services count=%s", len(api_services))

    databases = build_database_runtime(spans, metrics)
    if databases:
        snapshot["database_runtime"] = {"databases": databases}
    LOGGER.info("opentelemetry.databases count=%s", len(databases))

    storage_resources = build_storage_runtime(metrics)
    if storage_resources:
        snapshot["storage_runtime"] = {"resources": storage_resources}
    LOGGER.info("opentelemetry.storage_resources count=%s", len(storage_resources))

    flow_runtime = build_flow_runtime(flow, spans, metrics)
    if flow_runtime:
        snapshot["flow_runtime"] = flow_runtime
    LOGGER.info("opentelemetry.flow_runtime present=%s", bool(flow_runtime))

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
    components = build_flow_components(flow.get("components", {}), spans)

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
        "owner": flow.get("owner") or flow.get("team"),
        "criticality": flow.get("criticality") or flow.get("tier"),
        "business_impact": flow.get("business_impact"),
        "affected_services": flow.get("affected_services") or flow.get("services") or [],
        "blast_radius": flow.get("blast_radius", {}),
        "signals": signals,
        "components": components,
    }


def build_flow_components(explicit_components, spans):
    components = {
        name: dict(component or {})
        for name, component in (explicit_components or {}).items()
        if isinstance(component, dict)
    }
    trace_components = {}

    for span in spans:
        component_name = span_component_name(span)
        if not component_name:
            continue

        component_type = span_component_type(span)
        component = components.setdefault(
            component_name,
            {
                "type": component_type,
                "signals": {},
                "depends_on": [],
            },
        )
        component.setdefault("type", component_type)
        component.setdefault("signals", {})
        component.setdefault("depends_on", [])

        duration = span_duration_ms(span)
        if span_is_error(span) or span_is_timeout(span):
            component["signals"]["unhealthy"] = True
        if duration is not None and span_component_latency_unhealthy(component_type, duration):
            component["signals"]["unhealthy"] = True
        if span_recent_deployment(span):
            component["signals"]["recent_deployment"] = True

        trace_id = span.get("trace_id")
        if trace_id:
            trace_components.setdefault(trace_id, set()).add(component_name)

    add_trace_dependencies(components, trace_components)
    return components


def span_component_name(span):
    attributes = span_attributes(span)
    if span_is_database(span):
        return span_database_name(span)
    if span_is_kafka(span):
        return span_kafka_name(span)
    return span.get("service") or span.get("service_name")


def span_component_type(span):
    if span_is_database(span):
        return "database"
    if span_is_kafka(span):
        kind = str(span.get("kind") or span_attributes(span).get("span.kind") or "").lower()
        operation = str(span_attributes(span).get("messaging.operation") or "").lower()
        if "receive" in operation or "consumer" in kind:
            return "consumer"
        if "send" in operation or "producer" in kind:
            return "kafka"
        return "kafka"
    return "api"


def span_is_kafka(span):
    attributes = span_attributes(span)
    system = str(attributes.get("messaging.system") or "").lower()
    destination = attributes.get("messaging.destination.name") or attributes.get(
        "messaging.kafka.topic"
    )
    return system == "kafka" or bool(destination)


def span_kafka_name(span):
    attributes = span_attributes(span)
    return (
        attributes.get("messaging.destination.name")
        or attributes.get("messaging.kafka.topic")
        or span.get("service")
        or "kafka"
    )


def span_component_latency_unhealthy(component_type, duration_ms):
    if component_type == "database":
        return duration_ms >= 500
    if component_type == "api":
        return duration_ms >= 1000
    return duration_ms >= 1500


def add_trace_dependencies(components, trace_components):
    for names in trace_components.values():
        api_names = sorted(
            name for name in names if components.get(name, {}).get("type") == "api"
        )
        kafka_names = sorted(
            name for name in names if components.get(name, {}).get("type") == "kafka"
        )
        consumer_names = sorted(
            name for name in names if components.get(name, {}).get("type") == "consumer"
        )
        database_names = sorted(
            name for name in names if components.get(name, {}).get("type") == "database"
        )

        for kafka in kafka_names:
            add_depends_on(components[kafka], api_names)
        for consumer in consumer_names:
            add_depends_on(components[consumer], kafka_names or api_names)
        for database in database_names:
            add_depends_on(components[database], consumer_names or api_names)


def add_depends_on(component, dependencies):
    depends_on = component.setdefault("depends_on", [])
    for dependency in dependencies:
        if dependency and dependency not in depends_on:
            depends_on.append(dependency)


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
