import json
from datetime import datetime

import yaml


DEGRADATION_RULE_IDS = {
    "flow.runtime.downstream_db_bottleneck",
    "flow.runtime.deployment_correlated_degradation",
    "flow.runtime.cascading_latency",
    "deployment.window.api_latency_regression",
    "deployment.window.error_rate_regression",
    "deployment.window.kafka_lag_regression",
    "api.runtime.deployment_correlated_degradation",
    "api.runtime.error_rate.high",
    "api.runtime.latency_p95.high",
    "api.runtime.timeout_rate.high",
    "api.runtime.retry_amplification",
    "database.runtime.latency.high",
    "database.runtime.connection_pool.exhaustion",
    "database.runtime.lock_contention.high",
    "kafka.consumer_group.lag.high",
    "kafka.consumer_group.rebalancing",
    "kafka.consumer_group.member_churn.high",
    "kafka.history.consumer_lag.growing",
    "kafka.history.deployment_correlated_lag",
    "kafka.runtime.consumer_lag.increasing_under_pressure",
    "kafka.runtime.rebalance_storm",
    "kafka.runtime.consumer_group.unstable",
    "k8s.runtime.deployment.unavailable",
    "k8s.runtime.pod.crash_loop",
    "k8s.runtime.pod.pending",
}


def analyze_deployment_events_file(path, existing_findings=None):
    path_string = str(path)
    with open(path_string, "r") as f:
        if path_string.endswith(".json"):
            data = json.load(f) or {}
        else:
            data = yaml.safe_load(f) or {}

    return analyze_deployment_events(
        data, existing_findings=existing_findings or [], source=path_string
    )


def analyze_deployment_events(data, existing_findings=None, source="deployment-events"):
    events = normalize_deployment_events(data)
    findings = []

    if not events:
        return [
            deployment_finding(
                "deployment.events.empty",
                "LOW",
                "Deployment events input is empty",
                "Beacon did not receive deployment events to correlate with runtime degradation.",
                "Provide deployment_events with service, environment, deployed_at, and changed components.",
                source,
                {"event_count": 0},
            )
        ]

    findings.append(
        deployment_finding(
            "deployment.events.loaded",
            "INFO",
            f"Beacon loaded {len(events)} deployment event(s)",
            "Deployment events are available for read-only runtime correlation.",
            "Use deployment correlation with runtime findings to decide whether rollback or deployment inspection should come before scaling.",
            source,
            {"event_count": len(events), "events": event_summaries(events)},
        )
    )

    correlated = correlate_deployments_with_findings(events, existing_findings or [])
    if correlated:
        findings.append(correlated)

    findings.extend(analyze_deployment_windows(events, source))

    return findings


def normalize_deployment_events(data):
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = (
            data.get("deployment_events")
            or data.get("deployments")
            or data.get("events")
            or []
        )
    else:
        events = []

    normalized = []
    for event in events:
        if not isinstance(event, dict):
            continue
        normalized.append(
            {
                "service": event.get("service") or event.get("name") or "unknown",
                "environment": event.get("environment"),
                "version": event.get("version"),
                "deployed_at": event.get("deployed_at")
                or event.get("timestamp")
                or event.get("time"),
                "commit": event.get("commit") or event.get("sha"),
                "namespace": event.get("namespace"),
                "changed_components": event.get("changed_components", []) or [],
                "window_before": event.get("window_before")
                or event.get("before")
                or {},
                "window_after": event.get("window_after") or event.get("after") or {},
            }
        )

    return sorted(normalized, key=lambda event: event_time_key(event))


def analyze_deployment_windows(events, source):
    findings = []

    for event in events:
        before = event.get("window_before") or {}
        after = event.get("window_after") or {}

        if not before or not after:
            continue

        findings.extend(api_latency_regression(event, before, after, source))
        findings.extend(error_rate_regression(event, before, after, source))
        findings.extend(kafka_lag_regression(event, before, after, source))

    return findings


def api_latency_regression(event, before, after, source):
    before_value = metric_value(before, "api_latency_p95_ms", "latency_p95_ms")
    after_value = metric_value(after, "api_latency_p95_ms", "latency_p95_ms")

    if before_value is None or after_value is None:
        return []

    delta = after_value - before_value
    ratio = safe_ratio(after_value, before_value)
    if not (after_value >= 1000 and (delta >= 500 or ratio >= 2)):
        return []

    return [
        deployment_window_finding(
            "deployment.window.api_latency_regression",
            "HIGH",
            f"Deployment '{event['service']}' increased API p95 latency",
            "API latency increased materially after deployment, strengthening the deployment-regression hypothesis.",
            "Compare application traces, dependency latency, timeout policy, and deployment diff before scaling infrastructure.",
            source,
            event,
            "api_latency_p95_ms",
            before_value,
            after_value,
        )
    ]


def error_rate_regression(event, before, after, source):
    before_value = metric_value(before, "api_error_rate_percent", "error_rate_percent")
    after_value = metric_value(after, "api_error_rate_percent", "error_rate_percent")

    if before_value is None or after_value is None:
        return []

    delta = after_value - before_value
    ratio = safe_ratio(after_value, before_value)
    if not (after_value >= 5 and (delta >= 2 or ratio >= 2)):
        return []

    return [
        deployment_window_finding(
            "deployment.window.error_rate_regression",
            "HIGH",
            f"Deployment '{event['service']}' increased API error rate",
            "API error rate increased materially after deployment, pointing to rollout or application regression.",
            "Inspect error classes, rollback safety, feature flags, and dependency compatibility introduced by the deployment.",
            source,
            event,
            "api_error_rate_percent",
            before_value,
            after_value,
        )
    ]


def kafka_lag_regression(event, before, after, source):
    before_value = metric_value(
        before, "kafka_consumer_lag", "kafka_total_consumer_lag", "total_consumer_lag"
    )
    after_value = metric_value(
        after, "kafka_consumer_lag", "kafka_total_consumer_lag", "total_consumer_lag"
    )

    if before_value is None or after_value is None:
        return []

    delta = after_value - before_value
    ratio = safe_ratio(after_value, before_value)
    if not (after_value >= 10000 and (delta >= 10000 or ratio >= 2)):
        return []

    return [
        deployment_window_finding(
            "deployment.window.kafka_lag_regression",
            "HIGH",
            f"Deployment '{event['service']}' increased Kafka consumer lag",
            "Kafka consumer lag increased materially after deployment, which can indicate slower consumers, retries, or downstream degradation.",
            "Compare consumer deployment changes, processing latency, retry behavior, downstream latency, and partition-level lag.",
            source,
            event,
            "kafka_consumer_lag",
            before_value,
            after_value,
        )
    ]


def correlate_deployments_with_findings(events, findings):
    degradation = [
        finding
        for finding in findings
        if finding.get("rule_id") in DEGRADATION_RULE_IDS
        and finding.get("severity") in {"CRITICAL", "HIGH", "MEDIUM"}
    ]

    if not degradation:
        return None

    latest = events[-1]
    matched = degradation[:8]
    return deployment_finding(
        "deployment.runtime.degradation_correlated",
        "HIGH",
        "Runtime degradation is correlated with deployment events",
        "Recent deployment events are present alongside runtime degradation signals. Beacon cannot prove causality from timing alone, but deployment inspection or rollback safety should be evaluated before broad infrastructure scaling.",
        "Review deployment diff, rollout health, feature flags, changed components, consumer group churn, and rollback safety before scaling Kafka or other infrastructure.",
        matched[0].get("file", "deployment-correlation"),
        {
            "latest_deployment": latest,
            "deployment_count": len(events),
            "matched_rule_ids": sorted({finding.get("rule_id") for finding in matched}),
            "matched_findings": [
                {
                    "rule_id": finding.get("rule_id"),
                    "severity": finding.get("severity"),
                    "title": finding.get("title"),
                }
                for finding in matched
            ],
        },
    )


def event_summaries(events):
    return [
        {key: value for key, value in event.items() if value not in (None, "", [])}
        for event in events[:10]
    ]


def event_time_key(event):
    value = event.get("deployed_at") or ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def metric_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def safe_ratio(after_value, before_value):
    if before_value == 0:
        return float("inf") if after_value > 0 else 1
    return round(after_value / before_value, 2)


def deployment_window_finding(
    rule_id,
    severity,
    title,
    impact,
    recommendation,
    source,
    event,
    metric,
    before_value,
    after_value,
):
    return deployment_finding(
        rule_id,
        severity,
        title,
        impact,
        recommendation,
        source,
        {
            "service": event.get("service"),
            "version": event.get("version"),
            "deployed_at": event.get("deployed_at"),
            "namespace": event.get("namespace"),
            "metric": metric,
            "before": before_value,
            "after": after_value,
            "delta": after_value - before_value,
            "ratio": safe_ratio(after_value, before_value),
        },
    )


def deployment_finding(
    rule_id, severity, title, impact, recommendation, file, evidence
):
    return {
        "rule_id": rule_id,
        "domain": "deployment",
        "category": "runtime_stability",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence,
        "tags": ["deployment", "runtime", "correlation"],
    }
