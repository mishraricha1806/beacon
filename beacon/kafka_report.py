KAFKA_REPORT_GROUPS = [
    {
        "key": "security_access",
        "title": "Security & Access",
        "keywords": [
            ".security.",
            ".acl",
            "acl.",
            "access.",
            "plaintext",
            "authorizer",
            "allow_everyone",
            "quota",
            "quotas",
            "certificate",
        ],
        "action": "Tighten Kafka authentication, authorization, listener security, ACL scope, and quota controls.",
    },
    {
        "key": "broker_health",
        "title": "Broker Health",
        "keywords": [
            "broker",
            "controller",
            "under_replicated",
            "offline_partitions",
            "leader_imbalance",
            "replication_fetcher",
            "request_queue",
            "network_saturation",
        ],
        "action": "Stabilize brokers, controller/quorum health, replica placement, and broker capacity before production approval.",
    },
    {
        "key": "topic_safety",
        "title": "Topic Safety",
        "keywords": [
            "topic.",
            "partitions",
            "retention",
            "cleanup",
            "compaction",
            "message_bytes",
            "owner",
            "replica_placement",
        ],
        "action": "Fix topic replication, partitioning, retention, compaction, ownership, and placement guardrails.",
    },
    {
        "key": "consumer_lag",
        "title": "Consumer Lag & Groups",
        "keywords": [
            "consumer_group",
            "consumer.",
            "lag",
            "rebalance",
            "member_churn",
            "hot_partition",
            "auto_commit",
            "auto_offset",
            "heartbeat",
            "poll_interval",
            "dlq",
        ],
        "action": "Stabilize consumer groups, reduce lag growth, review retry/DLQ behavior, and check downstream bottlenecks.",
    },
    {
        "key": "trend_churn",
        "title": "Trend & Churn",
        "keywords": [
            "history",
            "churn",
            "growing",
            "trend",
            "growth",
            "controller_churn",
            "rebalance_churn",
        ],
        "action": "Investigate what changed over time and compare trends against deployments, traffic, and capacity events.",
    },
    {
        "key": "schema_safety",
        "title": "Schema Safety",
        "keywords": [
            "schema",
            "schema_registry",
            "compatibility",
            "poison",
        ],
        "action": "Enforce safe schema compatibility, expected subjects, and schema-aware producer/consumer rollout controls.",
    },
    {
        "key": "recovery_replay",
        "title": "Recovery & Replay",
        "keywords": [
            "replay",
            "recovery",
            "transaction",
            "producer",
            "offsets",
            "retention_window",
            "drain_capacity",
        ],
        "action": "Validate replay time, retention windows, transactional durability, and recovery runbooks.",
    },
]


def build_kafka_report(findings):
    kafka_findings = [finding for finding in findings if finding.get("domain") == "kafka"]
    if not kafka_findings:
        return None

    sections = []
    assigned_ids = set()

    for group in KAFKA_REPORT_GROUPS:
        grouped = [
            finding
            for finding in kafka_findings
            if id(finding) not in assigned_ids and matches_group(finding, group)
        ]
        for finding in grouped:
            assigned_ids.add(id(finding))

        if grouped:
            sections.append(build_section(group, grouped))

    remaining = [finding for finding in kafka_findings if id(finding) not in assigned_ids]
    if remaining:
        sections.append(
            build_section(
                {
                    "key": "other",
                    "title": "Other Kafka Findings",
                    "action": "Review remaining Kafka findings and route them to the owning platform team.",
                },
                remaining,
            )
        )

    return {
        "title": "Kafka Operational Readiness",
        "finding_count": len(kafka_findings),
        "section_count": len(sections),
        "sections": sections,
    }


def matches_group(finding, group):
    rule_id = str(finding.get("rule_id") or "").lower()
    if rule_id.startswith("kafka.history.") and group["key"] != "trend_churn":
        return False
    if "schema" in rule_id and group["key"] != "schema_safety":
        return False
    if rule_id.startswith("schema_registry.") and group["key"] != "schema_safety":
        return False
    if rule_id.startswith("kafka.topic.") and group["key"] not in {
        "topic_safety",
        "schema_safety",
        "recovery_replay",
    }:
        return False
    if rule_id.startswith("kafka.producer.") and group["key"] != "recovery_replay":
        return False
    if rule_id.startswith("kafka.consumer.") and group["key"] not in {
        "consumer_lag",
        "recovery_replay",
    }:
        return False

    haystack = " ".join(
        str(value or "")
        for value in [
            finding.get("rule_id"),
            finding.get("title"),
            finding.get("impact"),
            finding.get("recommendation"),
            " ".join(finding.get("tags") or []),
        ]
    ).lower()

    return any(keyword.lower() in haystack for keyword in group["keywords"])


def build_section(group, findings):
    severity_counts = count_severities(findings)
    top_findings = sorted(findings, key=finding_priority)[:5]

    return {
        "key": group["key"],
        "title": group["title"],
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "top_findings": [
            {
                "rule_id": finding.get("rule_id"),
                "severity": finding.get("severity"),
                "title": finding.get("title"),
                "recommendation": finding.get("recommendation"),
            }
            for finding in top_findings
        ],
        "recommended_action": group["action"],
    }


def count_severities(findings):
    counts = {
        "CRITICAL": 0,
        "ERROR": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "INFO": 0,
    }
    for finding in findings:
        severity = finding.get("severity", "INFO")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def finding_priority(finding):
    priority = {
        "ERROR": 0,
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4,
        "INFO": 5,
    }
    return priority.get(finding.get("severity"), 99)
