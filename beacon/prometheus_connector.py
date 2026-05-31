import json
import urllib.parse
import urllib.request

import yaml

from beacon.runtime_snapshot import analyze_runtime_snapshot
from beacon.runtime_advisor import evaluate_kafka_runtime


def analyze_prometheus_config(path, timeout=5):
    snapshot, collection_findings = collect_prometheus_snapshot(path, timeout=timeout)
    findings = list(collection_findings)
    kafka_runtime = snapshot.pop("kafka_runtime", None)

    if snapshot:
        findings.extend(analyze_runtime_snapshot(snapshot, source=path))

    if kafka_runtime:
        findings.extend(evaluate_kafka_runtime(kafka_runtime, path))

    return findings


def collect_prometheus_snapshot(path, timeout=5):
    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}

    prometheus = config.get("prometheus", config)
    base_url = prometheus.get("url")

    if not base_url:
        return {}, [
            prometheus_finding(
                "prometheus.config.url.missing",
                "ERROR",
                "Prometheus URL is missing",
                "Beacon cannot query Prometheus without a base URL.",
                "Set prometheus.url in the collector config.",
                path,
                {"config": path},
            )
        ]

    snapshot = {}
    findings = [
        prometheus_finding(
            "prometheus.runtime.read_only_mode",
            "INFO",
            "Beacon Prometheus connector is running in read-only diagnostic mode",
            "Beacon will only query Prometheus metrics through the HTTP API.",
            "No Prometheus or workload mutation operation will be performed.",
            path,
            {"mode": "read_only", "mutation_allowed": False},
        )
    ]

    for section in (
        "api_runtime",
        "database_runtime",
        "storage_runtime",
        "flow_runtime",
        "kafka_runtime",
    ):
        if section in prometheus:
            snapshot[section] = collect_section(
                base_url,
                prometheus.get(section),
                section,
                path,
                findings,
                timeout,
            )

    return snapshot, findings


def collect_section(base_url, section_config, section_name, source, findings, timeout):
    if not isinstance(section_config, dict):
        return {}

    if section_name == "api_runtime":
        return {
            "services": collect_named_items(
                base_url, section_config.get("services", []), source, findings, timeout
            )
        }

    if section_name == "database_runtime":
        return {
            "databases": collect_named_items(
                base_url, section_config.get("databases", []), source, findings, timeout
            )
        }

    if section_name == "storage_runtime":
        return {
            "resources": collect_named_items(
                base_url, section_config.get("resources", []), source, findings, timeout
            )
        }

    if section_name == "flow_runtime":
        data = {"name": section_config.get("name", "unknown-flow")}
        data["signals"] = collect_signals(
            base_url, section_config.get("signals", {}), source, findings, timeout
        )
        components = {}
        for name, component in (section_config.get("components", {}) or {}).items():
            components[name] = {
                "type": component.get("type"),
                "depends_on": component.get("depends_on", []) or [],
                "signals": collect_signals(
                    base_url, component.get("signals", {}), source, findings, timeout
                ),
            }
        if components:
            data["components"] = components
        return data

    if section_name == "kafka_runtime":
        data = {
            key: value
            for key, value in section_config.items()
            if key not in {"queries", "signals"}
        }
        queries = section_config.get("queries", section_config.get("signals", {}))
        data.update(collect_signals(base_url, queries, source, findings, timeout))
        return data

    return {}


def collect_named_items(base_url, items, source, findings, timeout):
    collected = []

    for item in items or []:
        data = {
            key: value
            for key, value in item.items()
            if key not in {"queries", "signals"}
        }
        queries = item.get("queries", item.get("signals", {}))
        data.update(collect_signals(base_url, queries, source, findings, timeout))
        collected.append(data)

    return collected


def collect_signals(base_url, queries, source, findings, timeout):
    signals = {}

    for field, query_config in (queries or {}).items():
        query = (
            query_config.get("query")
            if isinstance(query_config, dict)
            else query_config
        )
        value_type = (
            query_config.get("type") if isinstance(query_config, dict) else None
        )
        label = query_config.get("label") if isinstance(query_config, dict) else None

        try:
            if value_type == "map":
                value = query_prometheus_map(
                    base_url, query, label=label, timeout=timeout
                )
            else:
                value = query_prometheus(base_url, query, timeout=timeout)
            signals[field] = coerce_value(value, value_type)
        except Exception as error:
            findings.append(
                prometheus_finding(
                    "prometheus.query.failed",
                    "ERROR",
                    f"Prometheus query failed for '{field}'",
                    "Beacon could not collect one or more Prometheus runtime signals.",
                    "Check the query, Prometheus URL, network access, and metric availability.",
                    source,
                    {"field": field, "query": query, "error": str(error)},
                )
            )

    return signals


def query_prometheus(base_url, query, timeout=5):
    params = urllib.parse.urlencode({"query": query})
    url = f"{base_url.rstrip('/')}/api/v1/query?{params}"

    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "success":
        raise ValueError(payload.get("error") or "Prometheus query did not succeed")

    result = payload.get("data", {}).get("result", [])

    if not result:
        return None

    value = result[0].get("value", [None, None])[1]

    if value is None:
        return None

    return float(value)


def query_prometheus_map(base_url, query, label, timeout=5):
    if not label:
        raise ValueError("Prometheus map query requires a label")

    params = urllib.parse.urlencode({"query": query})
    url = f"{base_url.rstrip('/')}/api/v1/query?{params}"

    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "success":
        raise ValueError(payload.get("error") or "Prometheus query did not succeed")

    result = payload.get("data", {}).get("result", [])
    mapped = {}

    for item in result:
        key = item.get("metric", {}).get(label)
        value = item.get("value", [None, None])[1]

        if key is None or value is None:
            continue

        mapped[str(key)] = float(value)

    return mapped


def coerce_value(value, value_type):
    if value_type == "bool":
        return bool(value)

    return value


def prometheus_finding(
    rule_id, severity, title, impact, recommendation, file, evidence
):
    return {
        "rule_id": rule_id,
        "domain": "prometheus",
        "category": "runtime_stability",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence,
        "tags": ["prometheus", "runtime", "collector"],
    }
