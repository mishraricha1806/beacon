import json
from datetime import datetime

import yaml


DEGRADATION_RULE_IDS = {
    "flow.runtime.downstream_db_bottleneck",
    "flow.runtime.deployment_correlated_degradation",
    "flow.runtime.cascading_latency",
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
            }
        )

    return sorted(normalized, key=lambda event: event_time_key(event))


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
