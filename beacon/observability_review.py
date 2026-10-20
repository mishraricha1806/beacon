"""Deterministic review of a service's observable operating posture.

This module evaluates declared evidence only. It does not query, mutate, or
configure an observability backend and it never treats missing evidence as proof
that a control exists.
"""

import json
from datetime import datetime, timezone

import yaml

from beacon.contracts import OBSERVABILITY_REVIEW_SCHEMA_VERSION
from beacon.input_validation import missing_path_finding, path_missing
from beacon.rules import finding

GOLDEN_SIGNALS = {"availability", "latency", "traffic", "errors", "saturation"}
SENSITIVE_TERMS = {
    "authorization",
    "cookie",
    "credit_card",
    "email",
    "password",
    "session",
    "ssn",
    "token",
}


def analyze_observability_review_file(path, now=None):
    """Load and evaluate a versioned observability review YAML or JSON file."""
    if path_missing(path):
        return [missing_path_finding(path)]

    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            payload = (
                json.load(file_obj) if str(path).endswith(".json") else yaml.safe_load(file_obj)
            )
    except (OSError, ValueError, yaml.YAMLError) as error:
        return [
            _finding(
                "observability.review.input_invalid",
                "ERROR",
                "Observability review input could not be loaded",
                "Beacon cannot establish observability readiness from malformed evidence.",
                "Fix the YAML or JSON input and rerun the review.",
                path,
                {"error": str(error)},
                confidence="HIGH",
                freshness="UNKNOWN",
            )
        ]

    return analyze_observability_review(payload, source=str(path), now=now)


def analyze_observability_review(payload, source="observability-review", now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, dict):
        return [_invalid(source, "The review document must be an object.")]

    review = payload.get("observability_review", payload)
    if not isinstance(review, dict):
        return [_invalid(source, "observability_review must be an object.")]
    if review.get("schema_version") != OBSERVABILITY_REVIEW_SCHEMA_VERSION:
        return [
            _invalid(
                source,
                f"schema_version must be {OBSERVABILITY_REVIEW_SCHEMA_VERSION}.",
            )
        ]
    shape_error = _shape_error(review)
    if shape_error:
        return [_invalid(source, shape_error)]

    service = review.get("service") or {}
    service_name = service.get("name") or "unknown-service"
    captured_at = review.get("captured_at")
    age_hours = _age_hours(captured_at, now)
    freshness = _freshness(age_hours, review.get("freshness_policy") or {})
    base = {
        "service": service_name,
        "owner": service.get("owner"),
        "tier": service.get("tier"),
        "captured_at": captured_at,
    }
    findings = []

    if not service.get("owner"):
        findings.append(
            _finding(
                "observability.service.owner_missing",
                "HIGH",
                f"Service '{service_name}' has no observability owner",
                "Alerts, SLOs, and telemetry gaps may remain unowned during an incident.",
                "Declare the accountable service or observability owner.",
                source,
                base,
                freshness=freshness,
            )
        )

    if age_hours is None:
        findings.append(
            _finding(
                "observability.evidence.timestamp_missing",
                "HIGH",
                "Observability evidence has no valid capture timestamp",
                "Beacon cannot determine whether the reviewed evidence still "
                "represents production.",
                "Set captured_at to an RFC 3339 timestamp and define a freshness policy.",
                source,
                base,
                confidence="HIGH",
                freshness="UNKNOWN",
            )
        )
    elif freshness == "STALE":
        findings.append(
            _finding(
                "observability.evidence.stale",
                "ERROR",
                f"Observability evidence for '{service_name}' is stale",
                "Release conclusions may be based on telemetry or configuration "
                "that no longer represents production.",
                "Refresh the evidence before using this review as a release gate.",
                source,
                {**base, "age_hours": round(age_hours, 2)},
                confidence="HIGH",
                freshness=freshness,
            )
        )

    findings.extend(_review_slos(review, source, base, freshness))
    findings.extend(_review_alerts(review, source, base, freshness))
    findings.extend(_review_dashboards(review, source, base, freshness))
    findings.extend(_review_telemetry(review, source, base, freshness, now))
    findings.extend(_review_synthetics(review, source, base, freshness))
    findings.extend(_review_incidents(review, source, base, freshness))
    findings.extend(_review_history(review, source, base, freshness))
    findings.extend(_review_deployments(review, source, base, freshness))

    if not findings:
        findings.append(
            _finding(
                "observability.review.controls_verified",
                "INFO",
                f"Observable operating controls are declared for '{service_name}'",
                "The supplied evidence covers the deterministic checks in this review contract.",
                "Retain the evidence, review changes in code review, and refresh it on schedule.",
                source,
                base,
                confidence="MEDIUM",
                freshness=freshness,
            )
        )
    return findings


def _review_slos(review, source, base, freshness):
    findings = []
    slos = review.get("slos") or []
    if not slos:
        return [
            _finding(
                "observability.slo.missing",
                "HIGH",
                "No service-level objective is declared",
                "The service cannot make an evidence-based reliability commitment "
                "or manage an error budget.",
                "Define at least one measurable availability or latency SLO with a rolling window.",
                source,
                base,
                freshness=freshness,
            )
        ]

    for slo in slos:
        if not isinstance(slo, dict):
            continue
        name = slo.get("name") or "unnamed-slo"
        target = _number(slo.get("target_percent"))
        window = _number(slo.get("window_days"))
        evidence = {**base, "slo": name, "target_percent": target, "window_days": window}
        if target is None or target <= 0 or target >= 100 or window is None or window <= 0:
            findings.append(
                _finding(
                    "observability.slo.invalid",
                    "ERROR",
                    f"SLO '{name}' is not measurable",
                    "An invalid target or window makes error-budget calculations unreliable.",
                    "Set target_percent between 0 and 100 and a positive window_days value.",
                    source,
                    evidence,
                    freshness=freshness,
                )
            )
        remaining = _number(slo.get("error_budget_remaining_percent"))
        if remaining is not None and remaining <= 0:
            findings.append(
                _finding(
                    "observability.error_budget.exhausted",
                    "CRITICAL",
                    f"SLO '{name}' has exhausted its error budget",
                    "Further reliability-impacting releases can violate the service commitment.",
                    "Apply the documented error-budget policy and prioritize reliability recovery.",
                    source,
                    {**evidence, "error_budget_remaining_percent": remaining},
                    confidence="HIGH",
                    freshness=freshness,
                )
            )
        windows = slo.get("burn_rate_alerts") or []
        valid_windows = {
            str(item.get("window"))
            for item in windows
            if isinstance(item, dict) and item.get("window") and _number(item.get("threshold"))
        }
        if len(valid_windows) < 2:
            findings.append(
                _finding(
                    "observability.slo.burn_rate_multi_window_missing",
                    "HIGH",
                    f"SLO '{name}' lacks a multi-window burn-rate alert",
                    "Fast burns or sustained slower burns may consume the error "
                    "budget without actionable detection.",
                    "Configure at least two paired burn-rate windows with explicit thresholds.",
                    source,
                    {**evidence, "valid_burn_rate_windows": sorted(valid_windows)},
                    freshness=freshness,
                )
            )
    return findings


def _review_alerts(review, source, base, freshness):
    findings = []
    alerts = review.get("alerts") or []
    if not alerts:
        return [
            _finding(
                "observability.alerts.missing",
                "HIGH",
                "No actionable alerts are declared",
                "Material service degradation may not reach an accountable responder.",
                "Declare symptom-based alerts with owners, routes, severities, and runbooks.",
                source,
                base,
                freshness=freshness,
            )
        ]
    required = ("owner", "route", "severity", "runbook_url")
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        missing = [key for key in required if not alert.get(key)]
        if missing:
            findings.append(
                _finding(
                    "observability.alert.governance_incomplete",
                    "HIGH",
                    f"Alert '{alert.get('name', 'unnamed-alert')}' is not actionable",
                    "Responders may not know who owns the alert, where it routes, "
                    "how urgent it is, or how to act.",
                    "Add owner, route, severity, and runbook_url to the alert definition.",
                    source,
                    {**base, "alert": alert.get("name"), "missing": missing},
                    confidence="HIGH",
                    freshness=freshness,
                )
            )
    return findings


def _review_dashboards(review, source, base, freshness):
    dashboards = review.get("dashboards") or []
    observed = set()
    for dashboard in dashboards:
        if isinstance(dashboard, dict):
            observed.update(str(item).lower() for item in dashboard.get("signals") or [])
    missing = sorted(GOLDEN_SIGNALS - observed)
    if not dashboards or missing:
        return [
            _finding(
                "observability.dashboard.critical_signals_missing",
                "HIGH",
                "Dashboards do not cover all critical service signals",
                "Operators may lack a shared view of customer impact, demand, "
                "failure, and resource pressure.",
                "Cover availability, latency, traffic, errors, and saturation on "
                "an owned service dashboard.",
                source,
                {**base, "missing_signals": missing or sorted(GOLDEN_SIGNALS)},
                freshness=freshness,
            )
        ]
    return []


def _review_telemetry(review, source, base, freshness, now):
    findings = []
    telemetry = review.get("telemetry") or {}
    signals = telemetry.get("signals") or {}
    missing = [name for name in ("metrics", "logs", "traces") if not signals.get(name)]
    if missing:
        findings.append(
            _finding(
                "observability.telemetry.signals_missing",
                "HIGH",
                "Required telemetry signals are missing",
                "Diagnosis and cross-signal validation will be incomplete during degradation.",
                "Provide metrics, logs, and traces or document an approved "
                "service-specific exception.",
                source,
                {**base, "missing_signals": missing},
                freshness=freshness,
            )
        )
    signal_ages = {}
    maximum_minutes = _number(telemetry.get("max_signal_age_minutes")) or 15
    for signal, last_seen in (telemetry.get("last_seen_at") or {}).items():
        age = _age_hours(last_seen, now)
        if age is None or age * 60 > maximum_minutes:
            signal_ages[str(signal)] = None if age is None else round(age * 60, 2)
    if signal_ages:
        findings.append(
            _finding(
                "observability.telemetry.data_stale",
                "ERROR",
                "Telemetry signals are stale or have invalid timestamps",
                "Missing recent samples can hide an outage or produce a false healthy conclusion.",
                "Restore telemetry delivery and verify recent samples before using "
                "the review as a gate.",
                source,
                {
                    **base,
                    "stale_signal_age_minutes": signal_ages,
                    "max_signal_age_minutes": maximum_minutes,
                },
                confidence="HIGH",
                freshness="STALE",
            )
        )
    if signals.get("traces") and not telemetry.get("trace_propagation_verified"):
        findings.append(
            _finding(
                "observability.trace.propagation_unverified",
                "HIGH",
                "End-to-end trace propagation is not verified",
                "Distributed requests may fragment into unrelated spans and hide "
                "the failing dependency.",
                "Verify trace-context propagation across ingress, asynchronous "
                "messaging, and downstream calls.",
                source,
                base,
                freshness=freshness,
            )
        )
    correlations = {str(item).lower() for item in telemetry.get("correlations") or []}
    required_correlations = {"logs_to_traces", "metrics_to_traces"}
    if not required_correlations.issubset(correlations):
        findings.append(
            _finding(
                "observability.telemetry.correlation_incomplete",
                "MEDIUM",
                "Logs, metrics, and traces are not fully correlated",
                "Responders must manually pivot across tools, increasing time to isolate a fault.",
                "Add trace IDs to logs and exemplars or equivalent metric-to-trace links.",
                source,
                {**base, "missing_correlations": sorted(required_correlations - correlations)},
                freshness=freshness,
            )
        )
    sampling = _number(telemetry.get("trace_sampling_ratio"))
    if sampling is None or sampling <= 0 or sampling > 1:
        findings.append(
            _finding(
                "observability.telemetry.sampling_invalid",
                "HIGH",
                "Trace sampling is missing or invalid",
                "Trace evidence may be absent, misleading, or unnecessarily expensive.",
                "Declare a sampling ratio greater than 0 and at most 1, with tail "
                "sampling for important failures where supported.",
                source,
                {**base, "trace_sampling_ratio": sampling},
                freshness=freshness,
            )
        )
    active = _number(telemetry.get("active_series"))
    series_budget = _number(telemetry.get("active_series_budget"))
    if active is not None and series_budget is not None and active > series_budget:
        findings.append(
            _finding(
                "observability.metrics.cardinality_budget_exceeded",
                "HIGH",
                "Metric cardinality exceeds the declared budget",
                "High-cardinality labels can increase cost and destabilize telemetry pipelines.",
                "Remove unbounded labels, aggregate dimensions, and enforce a "
                "series budget in CI and runtime monitoring.",
                source,
                {**base, "active_series": active, "active_series_budget": series_budget},
                confidence="HIGH",
                freshness=freshness,
            )
        )
    cost = _number(telemetry.get("monthly_cost"))
    cost_budget = _number(telemetry.get("monthly_cost_budget"))
    if cost is not None and cost_budget is not None and cost > cost_budget:
        findings.append(
            _finding(
                "observability.telemetry.cost_budget_exceeded",
                "MEDIUM",
                "Observability cost exceeds the declared monthly budget",
                "Uncontrolled telemetry volume can create material and "
                "unpredictable operating cost.",
                "Review retention, sampling, aggregation, unused metrics, and "
                "high-volume log sources.",
                source,
                {**base, "monthly_cost": cost, "monthly_cost_budget": cost_budget},
                confidence="HIGH",
                freshness=freshness,
            )
        )
    sensitive = []
    for field in telemetry.get("sensitive_fields_detected") or []:
        normalized = str(field).lower().replace("-", "_")
        if normalized in SENSITIVE_TERMS or any(term in normalized for term in SENSITIVE_TERMS):
            sensitive.append(str(field))
    if sensitive:
        findings.append(
            _finding(
                "observability.telemetry.sensitive_data_detected",
                "CRITICAL",
                "Potential sensitive data is present in telemetry",
                "Logs or traces may expose credentials, personal data, or regulated information.",
                "Stop ingestion of the affected fields, rotate exposed credentials, "
                "redact at source, and follow the incident process.",
                source,
                {**base, "detected_fields": sorted(sensitive)},
                confidence="HIGH",
                freshness=freshness,
            )
        )
    return findings


def _review_synthetics(review, source, base, freshness):
    checks = review.get("synthetics") or []
    healthy = [
        item
        for item in checks
        if isinstance(item, dict) and item.get("enabled") and item.get("owner")
    ]
    if not healthy:
        return [
            _finding(
                "observability.synthetic.coverage_missing",
                "MEDIUM",
                "No owned synthetic check covers the service",
                "Customer-visible failure may go undetected when internal telemetry "
                "appears healthy.",
                "Add an owned synthetic check for the primary customer journey and "
                "route failures to responders.",
                source,
                base,
                freshness=freshness,
            )
        ]
    return []


def _review_incidents(review, source, base, freshness):
    incomplete = []
    for incident in review.get("incidents") or []:
        if not isinstance(incident, dict):
            continue
        required = (
            "started_at",
            "detected_at",
            "mitigated_at",
            "resolved_at",
            "owner",
            "evidence_links",
        )
        missing = [key for key in required if not incident.get(key)]
        if missing:
            incomplete.append({"id": incident.get("id"), "missing": missing})
    if incomplete:
        return [
            _finding(
                "observability.incident.timeline_incomplete",
                "MEDIUM",
                "Incident timeline evidence is incomplete",
                "Detection and recovery performance cannot be audited or improved reliably.",
                "Record start, detection, mitigation, resolution, owner, and evidence "
                "links for each material incident.",
                source,
                {**base, "incomplete_incidents": incomplete},
                freshness=freshness,
            )
        ]
    return []


def _review_history(review, source, base, freshness):
    history = review.get("history") or {}
    snapshots = history.get("snapshots") or []
    minimum = int(_number(history.get("minimum_snapshots")) or 3)
    findings = []
    if len(snapshots) < minimum:
        findings.append(
            _finding(
                "observability.history.insufficient",
                "MEDIUM",
                "Historical observability evidence is insufficient",
                "An isolated snapshot cannot show deterioration, recurring failure, "
                "or whether remediation improved reliability.",
                "Retain enough comparable snapshots to evaluate trends across "
                "releases and incidents.",
                source,
                {**base, "snapshot_count": len(snapshots), "minimum_snapshots": minimum},
                freshness=freshness,
            )
        )
        return findings

    risk_metrics = {
        "error_rate_percent",
        "latency_p95_ms",
        "slo_burn_rate",
        "active_series",
        "monthly_cost",
    }
    degrading = []
    for metric in risk_metrics:
        values = [
            _number((snapshot.get("metrics") or {}).get(metric))
            for snapshot in snapshots
            if isinstance(snapshot, dict)
        ]
        values = [value for value in values if value is not None]
        if len(values) < minimum:
            continue
        recent = values[-minimum:]
        materially_higher = recent[-1] > (recent[0] * 1.2 if recent[0] else 0)
        if materially_higher and all(left <= right for left, right in zip(recent, recent[1:])):
            degrading.append({"metric": metric, "values": recent})
    if degrading:
        findings.append(
            _finding(
                "observability.history.degrading_trend",
                "HIGH",
                "Historical telemetry contains a sustained degrading trend",
                "Reliability, telemetry scale, or cost has worsened across comparable snapshots.",
                "Investigate the trend and establish whether a release, demand, "
                "or telemetry change caused it.",
                source,
                {**base, "degrading_metrics": degrading},
                confidence="MEDIUM",
                freshness=freshness,
            )
        )
    return findings


def _review_deployments(review, source, base, freshness):
    regressions = []
    for deployment in review.get("deployments") or []:
        if not isinstance(deployment, dict):
            continue
        before = deployment.get("before") or {}
        after = deployment.get("after") or {}
        for metric in ("error_rate_percent", "latency_p95_ms", "slo_burn_rate"):
            old = _number(before.get(metric))
            new = _number(after.get(metric))
            if old is None or new is None:
                continue
            threshold = 1 if old == 0 else old * 1.5
            if new > threshold:
                regressions.append(
                    {
                        "deployment": deployment.get("id") or deployment.get("version"),
                        "metric": metric,
                        "before": old,
                        "after": new,
                    }
                )
    if regressions:
        return [
            _finding(
                "observability.deployment.regression_detected",
                "HIGH",
                "Deployment windows contain material telemetry regressions",
                "A release is correlated with worsening customer or reliability signals.",
                "Inspect the deployment diff and rollback or mitigate before "
                "attributing the change to capacity alone.",
                source,
                {**base, "regressions": regressions},
                confidence="MEDIUM",
                freshness=freshness,
            )
        ]
    return []


def _invalid(source, message):
    return _finding(
        "observability.review.input_invalid",
        "ERROR",
        "Observability review contract is invalid",
        "Beacon cannot make a reliable observability-readiness conclusion from this document.",
        "Use the v1 observability review schema and correct the reported contract error.",
        source,
        {"error": message},
        confidence="HIGH",
        freshness="UNKNOWN",
    )


def _shape_error(review):
    mapping_fields = ("service", "freshness_policy", "telemetry", "history")
    list_fields = (
        "slos",
        "alerts",
        "dashboards",
        "synthetics",
        "incidents",
        "deployments",
    )
    for field in mapping_fields:
        if field in review and not isinstance(review[field], dict):
            return f"{field} must be an object."
    for field in list_fields:
        if field in review and not isinstance(review[field], list):
            return f"{field} must be an array."

    telemetry = review.get("telemetry") or {}
    for field in ("signals", "last_seen_at"):
        if field in telemetry and not isinstance(telemetry[field], dict):
            return f"telemetry.{field} must be an object."
    history = review.get("history") or {}
    if "snapshots" in history and not isinstance(history["snapshots"], list):
        return "history.snapshots must be an array."
    return None


def _finding(
    rule_id,
    severity,
    title,
    impact,
    recommendation,
    source,
    evidence,
    confidence="MEDIUM",
    freshness="CURRENT",
):
    evidence = dict(evidence or {})
    evidence["assessment"] = {
        "confidence": confidence,
        "freshness": freshness,
        "evidence_bound": True,
    }
    return finding(
        severity,
        title,
        impact,
        recommendation,
        source,
        rule_id=rule_id,
        domain="observability",
        category="observability_readiness",
        evidence=evidence,
        tags=["observability", "evidence-bound"],
    )


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _age_hours(value, now):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 3600)
    except (TypeError, ValueError):
        return None


def _freshness(age_hours, policy):
    if age_hours is None:
        return "UNKNOWN"
    maximum = _number(policy.get("max_age_hours")) or 24
    return "CURRENT" if age_hours <= maximum else "STALE"
