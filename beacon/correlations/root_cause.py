SEVERITY_WEIGHT = {
    "CRITICAL": 25,
    "HIGH": 15,
    "MEDIUM": 8,
    "LOW": 3,
    "ERROR": 10,
    "INFO": 0,
}


CORRELATION_PATTERNS = [
    {
        "id": "correlation.root_cause.downstream_database_bottleneck",
        "title": "Likely downstream database bottleneck",
        "description": (
            "Database latency or capacity pressure is aligned with API, Kafka, "
            "or Flow degradation signals."
        ),
        "recommendation": (
            "Investigate database latency, connection pools, locks, slow queries, "
            "and consumer processing before scaling Kafka or API replicas."
        ),
        "rule_ids": {
            "flow.runtime.downstream_db_bottleneck",
            "database.runtime.latency.high",
            "database.runtime.connection_pool.exhaustion",
            "database.runtime.lock_contention.high",
            "kafka.consumer_group.decision.consumer_side",
        },
        "domains": {"database", "flow", "kafka"},
        "domain_terms": {"database", "db"},
    },
    {
        "id": "correlation.root_cause.deployment_regression",
        "title": "Likely deployment-triggered degradation",
        "description": (
            "Runtime degradation is correlated with deployment signals across "
            "API or Flow findings."
        ),
        "recommendation": (
            "Review the deployment diff, rollout health, feature flags, and "
            "rollback safety before broad infrastructure scaling."
        ),
        "rule_ids": {
            "flow.runtime.deployment_correlated_degradation",
            "api.runtime.deployment_correlated_degradation",
        },
        "domains": {"api", "flow"},
        "domain_terms": {"deployment", "rollout"},
    },
    {
        "id": "correlation.root_cause.retry_cascade",
        "title": "Likely retry or timeout cascade",
        "description": (
            "API timeouts, retry amplification, and Flow cascade findings "
            "indicate a self-amplifying runtime failure."
        ),
        "recommendation": (
            "Reduce retry aggressiveness, add backoff and jitter, protect the "
            "saturated dependency, and consider throttling or rollback."
        ),
        "rule_ids": {
            "flow.runtime.cascading_latency",
            "api.runtime.retry_amplification",
            "api.runtime.timeout_rate.high",
        },
        "domains": {"api", "flow"},
        "domain_terms": {"retry", "timeout", "cascade"},
    },
    {
        "id": "correlation.root_cause.storage_capacity_pressure",
        "title": "Likely storage or capacity pressure",
        "description": (
            "Storage, database storage, or Kafka disk pressure findings point "
            "to capacity exhaustion risk."
        ),
        "recommendation": (
            "Create immediate headroom, review growth drivers, retention policy, "
            "backup freshness, and I/O saturation."
        ),
        "rule_ids": {
            "storage.runtime.capacity.high",
            "storage.runtime.growth_rate.high",
            "storage.runtime.iops_saturation.high",
            "database.runtime.storage_saturation",
            "kafka.runtime.disk_usage.critical",
            "kafka.runtime.disk_usage.high",
            "kafka.runtime.disk_growth.high",
        },
        "domains": {"storage", "database", "kafka"},
        "domain_terms": {"storage", "disk", "capacity", "i/o"},
    },
    {
        "id": "correlation.root_cause.kubernetes_workload_instability",
        "title": "Likely Kubernetes workload instability",
        "description": (
            "Node, pod, or deployment runtime findings suggest workload or "
            "cluster instability."
        ),
        "recommendation": (
            "Inspect node pressure, pod events, rollout status, readiness probes, "
            "and recent Kubernetes deployment changes."
        ),
        "rule_ids": {
            "k8s.runtime.node.not_ready",
            "k8s.runtime.node.pressure",
            "k8s.runtime.pod.crash_loop",
            "k8s.runtime.pod.pending",
            "k8s.runtime.deployment.unavailable",
        },
        "domains": {"kubernetes"},
        "domain_terms": {"kubernetes", "pod", "node", "deployment"},
    },
]


def correlate_findings(findings, limit=5):
    hypotheses = []

    for pattern in CORRELATION_PATTERNS:
        matched = match_pattern(pattern, findings)

        if not matched:
            continue

        score = correlation_score(matched)

        hypotheses.append(
            {
                "correlation_id": pattern["id"],
                "title": pattern["title"],
                "confidence": confidence_for_score(score, matched),
                "score": score,
                "description": pattern["description"],
                "recommendation": pattern["recommendation"],
                "evidence": build_evidence(matched),
                "matched_rule_ids": sorted({finding.get("rule_id") for finding in matched}),
            }
        )

    hypotheses.sort(key=lambda item: item["score"], reverse=True)

    return hypotheses[:limit]


def match_pattern(pattern, findings):
    matched = []

    for finding in findings:
        if finding.get("severity") == "INFO":
            continue

        if finding.get("rule_id") in pattern["rule_ids"]:
            matched.append(finding)
            continue

        text = " ".join(
            [
                str(finding.get("domain", "")),
                str(finding.get("category", "")),
                str(finding.get("title", "")),
                str(finding.get("impact", "")),
                str(finding.get("recommendation", "")),
                " ".join(finding.get("tags", []) or []),
            ]
        ).lower()

        if finding.get("domain") in pattern.get("domains", set()) and any(
            term in text for term in pattern["domain_terms"]
        ):
            matched.append(finding)

    return matched


def correlation_score(findings):
    domains = {finding.get("domain") for finding in findings if finding.get("domain")}
    base = sum(SEVERITY_WEIGHT.get(finding.get("severity"), 0) for finding in findings)
    return base + (len(domains) * 5)


def confidence_for_score(score, findings):
    domains = {finding.get("domain") for finding in findings if finding.get("domain")}
    has_critical = any(finding.get("severity") == "CRITICAL" for finding in findings)

    if score >= 60 and (len(domains) >= 2 or has_critical):
        return "HIGH"

    if score >= 30:
        return "MEDIUM"

    return "LOW"


def build_evidence(findings):
    return [
        {
            "rule_id": finding.get("rule_id"),
            "severity": finding.get("severity"),
            "domain": finding.get("domain"),
            "title": finding.get("title"),
            "evidence": finding.get("evidence", {}),
        }
        for finding in findings[:8]
    ]
