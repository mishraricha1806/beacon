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
        },
        "domains": {"database", "flow", "kafka"},
        "domain_terms": {"database", "db"},
        "required_domains": {"database", "flow"},
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
            "deployment.runtime.degradation_correlated",
            "deployment.window.api_latency_regression",
            "deployment.window.error_rate_regression",
            "deployment.window.kafka_lag_regression",
            "kafka.history.deployment_correlated_lag",
        },
        "domains": {"api", "flow", "deployment", "kafka"},
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
        "domains": {"api"},
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
        "domains": {"storage", "database"},
        "domain_terms": {"storage", "disk", "capacity", "i/o"},
    },
    {
        "id": "correlation.root_cause.kafka_single_broker_topology",
        "title": "Likely Kafka topology limitation: single broker",
        "description": (
            "A one-broker Kafka cluster explains RF=1 and ISR/failover findings. "
            "This may be acceptable for non-production environments but is unsafe for production HA."
        ),
        "recommendation": (
            "Confirm the environment intent. For production, use at least 3 brokers "
            "and configure topic replication/min ISR accordingly."
        ),
        "rule_ids": {
            "kafka.cluster.broker_count.low",
            "kafka.topic.replication_factor.low",
            "kafka.cluster.under_min_isr_partitions",
            "kafka.cluster.under_replicated_partitions",
        },
        "domains": {"kafka"},
        "domain_terms": {"broker", "replication", "isr"},
        "required_rule_ids": {"kafka.cluster.broker_count.low"},
    },
    {
        "id": "correlation.root_cause.kafka_schema_governance",
        "title": "Likely Kafka schema governance risk",
        "description": (
            "Schema Registry compatibility settings allow unsafe schema evolution "
            "that can break consumers during producer deployments."
        ),
        "recommendation": (
            "Use BACKWARD, FULL, or an approved compatibility mode and validate "
            "subject-level overrides for critical topics."
        ),
        "rule_ids": {
            "schema_registry.compatibility.global_unsafe",
            "schema_registry.subject.compatibility.unsafe",
            "schema_registry.topic.subject.missing",
            "kafka.topic.schema_compatibility.unsafe",
        },
        "domains": {"kafka"},
        "domain_terms": {"schema", "compatibility"},
    },
    {
        "id": "correlation.root_cause.kafka_payload_storage_growth",
        "title": "Likely Kafka payload and retention growth risk",
        "description": (
            "Large message limits, unbounded retention, or retention guardrail gaps "
            "can create broker disk growth and recovery pressure."
        ),
        "recommendation": (
            "Review large-payload topics, move oversized payloads to object storage "
            "where appropriate, and set retention.ms/retention.bytes based on replay and disk capacity."
        ),
        "rule_ids": {
            "kafka.topic.max_message_bytes.large",
            "kafka.topic.retention_ms.unbounded",
            "kafka.topic.retention_bytes.missing",
            "kafka.topic.compacted_without_retention_bytes",
        },
        "domains": {"kafka"},
        "domain_terms": {"message", "payload", "retention"},
    },
    {
        "id": "correlation.root_cause.kafka_consumer_observation",
        "title": "Kafka consumer group observation: offsets or lag need context",
        "description": (
            "Consumer group offset or lag findings were observed, but Beacon should "
            "not infer downstream systems without flow/database telemetry."
        ),
        "recommendation": (
            "Check whether the consumer group is expected to be active, then compare "
            "lag trend with producer rate and application logs."
        ),
        "rule_ids": {
            "kafka.consumer_group.offsets.missing",
            "kafka.consumer_group.lag.low",
            "kafka.consumer_group.lag.moderate",
            "kafka.consumer_group.lag.high",
            "kafka.consumer_group.decision.consumer_side",
            "kafka.consumer_group.decision.no_urgent_action",
        },
        "domains": {"kafka"},
        "domain_terms": {"consumer", "lag", "offset"},
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
                "matched_rule_ids": sorted(
                    {finding.get("rule_id") for finding in matched}
                ),
            }
        )

    hypotheses = suppress_generic_hypotheses(hypotheses)
    hypotheses.sort(key=lambda item: item["score"], reverse=True)

    return hypotheses[:limit]


def suppress_generic_hypotheses(hypotheses):
    correlation_ids = {hypothesis["correlation_id"] for hypothesis in hypotheses}

    if "correlation.root_cause.kafka_payload_storage_growth" in correlation_ids:
        hypotheses = [
            hypothesis
            for hypothesis in hypotheses
            if hypothesis["correlation_id"]
            != "correlation.root_cause.storage_capacity_pressure"
        ]

    return hypotheses


def match_pattern(pattern, findings):
    matched = []
    required_rule_ids = pattern.get("required_rule_ids", set())
    required_domains = pattern.get("required_domains", set())

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

    if required_rule_ids:
        matched_rule_ids = {finding.get("rule_id") for finding in matched}
        if not required_rule_ids <= matched_rule_ids:
            return []

    if required_domains:
        matched_domains = {finding.get("domain") for finding in matched}
        if not matched_domains.intersection(required_domains):
            return []

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
