import re
from collections import Counter, defaultdict


SEVERITY_ORDER = {
    "ERROR": 0,
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
    "INFO": 5,
}

NONPROD_MARKERS = (
    "nonprod",
    "non-prod",
    "_dev",
    "-dev",
    ".dev",
    "development",
    "sandbox",
    "poc",
    "test",
)

ENV_DOWNGRADES = {
    "kafka.cluster.broker_count.low": "INFO",
    "kafka.topic.replication_factor.low": "INFO",
    "kafka.broker.default_replication_factor.low": "INFO",
    "kafka.broker.offsets_replication_factor.low": "INFO",
    "kafka.broker.transaction_log_replication_factor.low": "INFO",
}

CONTEXTUAL_SEVERITIES = {
    "kafka.topic.partitions.low": "LOW",
    "kafka.consumer_group.offsets.missing": "INFO",
    "kafka.topic.owner.missing": "LOW",
    "topology.service.owner.missing": "LOW",
}

ROLLUP_RULES = {
    "kafka.cluster.broker_count.low": {
        "key": "kafka.single_broker_cluster",
        "title": "Kafka cluster has a single broker",
        "category": "resiliency",
        "recommendation": "Confirm this is intentional for the environment. Use at least 3 brokers for production high availability.",
    },
    "kafka.topic.replication_factor.low": {
        "key": "kafka.topic_rf_low",
        "title": "Kafka topics have replication factor 1",
        "category": "resiliency",
        "recommendation": "Treat this as a derivative of broker count when the cluster has one broker; otherwise raise topic replication factor.",
    },
    "kafka.topic.partitions.low": {
        "key": "kafka.topic_low_partitions",
        "title": "Kafka topics have low partition count",
        "category": "scalability",
        "recommendation": "Validate against ordering requirements, throughput, producer rate, and consumer lag before increasing partitions.",
    },
    "kafka.topic.owner.missing": {
        "key": "kafka.topic_owner_missing",
        "title": "Kafka topics are missing owner metadata",
        "category": "operational_safety",
        "recommendation": "Add owner metadata for production governance, incident routing, and cleanup decisions.",
    },
    "kafka.consumer_group.offsets.missing": {
        "key": "kafka.consumer_offsets_missing",
        "title": "Kafka consumer groups have no committed offsets",
        "category": "runtime_stability",
        "recommendation": "Treat as an observation unless the group is expected to be active or has traffic/lag evidence.",
    },
    "kafka.topic.max_message_bytes.large": {
        "key": "kafka.large_messages",
        "title": "Kafka topics allow messages larger than 1MB",
        "category": "storage_sustainability",
        "recommendation": "Review whether large payloads should move to object storage with references in Kafka.",
    },
    "kafka.topic.retention_ms.unbounded": {
        "key": "kafka.unbounded_retention",
        "title": "Kafka topics have unbounded retention",
        "category": "storage_sustainability",
        "recommendation": "Set retention.ms or retention.bytes based on replay, compliance, and broker disk capacity.",
    },
    "schema_registry.compatibility.global_unsafe": {
        "key": "schema_registry_global_compatibility",
        "title": "Schema Registry global compatibility is unsafe",
        "category": "operational_safety",
        "recommendation": "Use BACKWARD, FULL, or an approved compatibility mode for production event schemas.",
    },
}


def infer_environment(findings, explicit=None):
    if explicit:
        return explicit

    haystack = " ".join(
        str(value)
        for finding in findings
        for value in (
            finding.get("title"),
            finding.get("file"),
            finding.get("impact"),
            finding.get("recommendation"),
            finding.get("evidence"),
        )
        if value
    ).lower()

    if any(marker in haystack for marker in NONPROD_MARKERS):
        return "nonprod"

    return "prod"


def interpret_findings(findings, environment=None):
    environment = infer_environment(findings, explicit=environment)
    single_broker = any(
        finding.get("rule_id") == "kafka.cluster.broker_count.low"
        for finding in findings
    )

    interpreted = []
    for finding in findings:
        adjusted = dict(finding)
        adjusted["original_severity"] = finding.get("severity")
        adjusted["severity"] = adjusted_severity(finding, environment, single_broker)
        if adjusted["severity"] != finding.get("severity"):
            adjusted["severity_adjustment_reason"] = adjustment_reason(
                finding, environment, single_broker
            )
        interpreted.append(adjusted)

    grouped_risks = build_grouped_risks(interpreted, environment)
    score_findings = grouped_risks_to_findings(grouped_risks, interpreted)

    return {
        "environment": environment,
        "findings": interpreted,
        "grouped_risks": grouped_risks,
        "score_findings": score_findings,
    }


def adjusted_severity(finding, environment, single_broker):
    rule_id = finding.get("rule_id")
    severity = finding.get("severity")

    if environment != "prod" and rule_id in ENV_DOWNGRADES:
        return ENV_DOWNGRADES[rule_id]

    if (
        single_broker
        and environment != "prod"
        and rule_id == "kafka.topic.replication_factor.low"
    ):
        return "INFO"

    return CONTEXTUAL_SEVERITIES.get(rule_id, severity)


def adjustment_reason(finding, environment, single_broker):
    rule_id = finding.get("rule_id")
    if environment != "prod" and rule_id in ENV_DOWNGRADES:
        return f"Downgraded because environment is {environment}."
    if single_broker and rule_id == "kafka.topic.replication_factor.low":
        return "Downgraded as derivative of single-broker cluster topology."
    if rule_id == "kafka.topic.partitions.low":
        return "Partition count needs throughput, ordering, and lag context before being treated as high risk."
    if rule_id == "kafka.consumer_group.offsets.missing":
        return "Missing offsets are observational unless the group is expected to be active."
    return "Adjusted by readiness interpretation policy."


def build_grouped_risks(findings, environment):
    grouped = {}
    examples = defaultdict(list)
    severities = defaultdict(list)
    categories = {}

    for finding in findings:
        rule_id = finding.get("rule_id")
        group_def = ROLLUP_RULES.get(rule_id)
        if not group_def:
            continue

        key = group_def["key"]
        grouped[key] = group_def
        severities[key].append(finding.get("severity", "INFO"))
        categories[key] = group_def["category"]
        if len(examples[key]) < 5:
            examples[key].append(extract_entity_name(finding))

    risks = []
    for key, group_def in grouped.items():
        count = len(severities[key])
        severity = highest_severity(severities[key])
        if key == "kafka.topic_rf_low" and has_group(
            grouped, "kafka.single_broker_cluster"
        ):
            title = f"{group_def['title']} because the cluster has one broker"
        else:
            title = group_def["title"]

        risks.append(
            {
                "key": key,
                "severity": severity,
                "title": title,
                "affected_count": count,
                "category": categories[key],
                "examples": [item for item in examples[key] if item],
                "recommendation": group_def["recommendation"],
                "environment": environment,
            }
        )

    return sort_grouped_risks(risks)


def grouped_risks_to_findings(grouped_risks, interpreted_findings):
    grouped_rule_ids = set(ROLLUP_RULES)
    score_findings = [
        {
            "severity": risk["severity"],
            "category": risk["category"],
            "rule_id": risk["key"],
            "title": risk["title"],
        }
        for risk in grouped_risks
    ]

    for finding in interpreted_findings:
        if finding.get("rule_id") not in grouped_rule_ids:
            score_findings.append(finding)

    return sort_findings(score_findings)


def sort_findings(findings):
    return sorted(
        findings,
        key=lambda finding: (
            SEVERITY_ORDER.get(finding.get("severity"), 99),
            finding.get("rule_id", ""),
            finding.get("title", ""),
        ),
    )


def sort_grouped_risks(risks):
    return sorted(
        risks,
        key=lambda risk: (
            SEVERITY_ORDER.get(risk.get("severity"), 99),
            -risk.get("affected_count", 0),
            risk.get("title", ""),
        ),
    )


def highest_severity(severities):
    return min(
        severities or ["INFO"], key=lambda severity: SEVERITY_ORDER.get(severity, 99)
    )


def has_group(grouped, key):
    return key in grouped


def extract_entity_name(finding):
    evidence = finding.get("evidence") or {}
    for key in ("topic", "name", "consumer_group", "group_id", "resource"):
        if evidence.get(key):
            return str(evidence[key])

    title = finding.get("title") or ""
    quoted = re.findall(r"'([^']+)'", title)
    if quoted:
        return quoted[0]

    return title


def severity_counter(findings):
    return Counter(finding.get("severity") for finding in findings)
