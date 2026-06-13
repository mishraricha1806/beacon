import re
from collections import Counter, defaultdict

from beacon.intelligence.context import (
    context_environment,
    kafka_environment_policy,
    rule_context_override,
    topic_context,
)


SEVERITY_ORDER = {
    "ERROR": 0,
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
    "INFO": 5,
}

RISK_POINTS = {
    "ERROR": 100,
    "CRITICAL": 100,
    "HIGH": 50,
    "MEDIUM": 20,
    "LOW": 5,
    "INFO": 0,
}

BUSINESS_CATEGORIES = {
    "resiliency": "Availability",
    "runtime_stability": "Performance",
    "scalability": "Performance",
    "storage_sustainability": "Capacity",
    "recovery_readiness": "Availability",
    "operational_safety": "Security",
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
        "business_category": "Availability",
        "recommendation": "Confirm this is intentional for the environment. Use at least 3 brokers for production high availability.",
        "remediation_command": "Provision at least 3 Kafka brokers for production high availability.",
    },
    "kafka.topic.replication_factor.low": {
        "key": "kafka.topic_rf_low",
        "title": "Kafka topics have replication factor 1",
        "category": "resiliency",
        "business_category": "Availability",
        "recommendation": "Treat this as a derivative of broker count when the cluster has one broker; otherwise raise topic replication factor.",
        "remediation_command": "Use kafka-reassign-partitions with a reassignment JSON that places replicas across at least 3 brokers.",
    },
    "kafka.topic.partitions.low": {
        "key": "kafka.topic_low_partitions",
        "title": "Kafka topics have low partition count",
        "category": "scalability",
        "business_category": "Performance",
        "recommendation": "Validate against ordering requirements, throughput, producer rate, and consumer lag before increasing partitions.",
        "remediation_command": "kafka-topics --bootstrap-server <bootstrap> --alter --topic <topic> --partitions <target-partitions>",
    },
    "kafka.topic.owner.missing": {
        "key": "kafka.topic_owner_missing",
        "title": "Kafka topics are missing owner metadata",
        "category": "operational_safety",
        "business_category": "Governance",
        "recommendation": "Add owner metadata for production governance, incident routing, and cleanup decisions.",
        "remediation_command": "Add owner/team metadata in the topic catalog, Terraform, Helm values, or service ownership registry.",
    },
    "kafka.consumer_group.offsets.missing": {
        "key": "kafka.consumer_offsets_missing",
        "title": "Kafka consumer groups have no committed offsets",
        "category": "runtime_stability",
        "business_category": "Performance",
        "recommendation": "Treat as an observation unless the group is expected to be active or has traffic/lag evidence.",
        "remediation_command": "Verify the consumer is active and committing offsets; no Kafka mutation is recommended by default.",
    },
    "kafka.topic.max_message_bytes.large": {
        "key": "kafka.large_messages",
        "title": "Kafka topics allow messages larger than 1MB",
        "category": "storage_sustainability",
        "business_category": "Capacity",
        "recommendation": "Review whether large payloads should move to object storage with references in Kafka.",
        "remediation_command": "kafka-configs --bootstrap-server <bootstrap> --alter --entity-type topics --entity-name <topic> --add-config max.message.bytes=1048576",
    },
    "kafka.topic.retention_ms.unbounded": {
        "key": "kafka.unbounded_retention",
        "title": "Kafka topics have unbounded retention",
        "category": "storage_sustainability",
        "business_category": "Capacity",
        "recommendation": "Set retention.ms or retention.bytes based on replay, compliance, and broker disk capacity.",
        "remediation_command": "kafka-configs --bootstrap-server <bootstrap> --alter --entity-type topics --entity-name <topic> --add-config retention.ms=<approved-ms>",
    },
    "schema_registry.compatibility.global_unsafe": {
        "key": "schema_registry_global_compatibility",
        "title": "Schema Registry global compatibility is unsafe",
        "category": "operational_safety",
        "business_category": "Governance",
        "recommendation": "Use BACKWARD, FULL, or an approved compatibility mode for production event schemas.",
        "remediation_command": "curl -X PUT <schema-registry-url>/config -H 'Content-Type: application/vnd.schemaregistry.v1+json' -d '{\"compatibility\":\"BACKWARD\"}'",
    },
}


def infer_environment(findings, explicit=None, intelligence_context=None):
    if isinstance(explicit, str) and explicit:
        return explicit

    contextual_environment = context_environment(intelligence_context)
    if contextual_environment:
        return contextual_environment

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


def interpret_findings(findings, environment=None, intelligence_context=None):
    environment = infer_environment(
        findings, explicit=environment, intelligence_context=intelligence_context
    )
    single_broker = any(
        finding.get("rule_id") == "kafka.cluster.broker_count.low" for finding in findings
    )

    interpreted = []
    for finding in findings:
        adjusted = dict(finding)
        adjusted["original_severity"] = finding.get("severity")
        adjusted["severity"] = adjusted_severity(
            finding, environment, single_broker, intelligence_context
        )
        if adjusted["severity"] != finding.get("severity"):
            adjusted["severity_adjustment_reason"] = adjustment_reason(
                finding, environment, single_broker, intelligence_context
            )
        interpreted.append(adjusted)

    grouped_risks = build_grouped_risks(interpreted, environment)
    score_findings = grouped_risks_to_findings(grouped_risks, interpreted)

    return {
        "environment": environment,
        "findings": interpreted,
        "grouped_risks": grouped_risks,
        "score_findings": score_findings,
        "risk_points": calculate_risk_points(score_findings),
    }


def adjusted_severity(finding, environment, single_broker, intelligence_context=None):
    rule_id = finding.get("rule_id")
    severity = finding.get("severity")

    context_override = rule_context_override(intelligence_context, rule_id, environment)
    if context_override.get("severity"):
        return context_override["severity"]

    kafka_policy = kafka_environment_policy(intelligence_context, environment)
    if (
        rule_id == "kafka.cluster.broker_count.low"
        and kafka_policy.get("allow_single_broker") is True
    ):
        return "INFO"

    if (
        rule_id == "kafka.topic.replication_factor.low"
        and kafka_policy.get("allow_replication_factor_one") is True
    ):
        return "INFO"

    topic_policy = topic_context(intelligence_context, extract_entity_name(finding))
    if (
        rule_id == "kafka.topic.partitions.low"
        and topic_policy.get("low_partitions_allowed") is True
    ):
        return topic_policy.get("severity", "INFO")

    if (
        rule_id == "kafka.topic.owner.missing"
        and kafka_policy.get("require_owner_metadata") is False
    ):
        return "INFO"

    if environment != "prod" and rule_id in ENV_DOWNGRADES:
        return ENV_DOWNGRADES[rule_id]

    if single_broker and environment != "prod" and rule_id == "kafka.topic.replication_factor.low":
        return "INFO"

    return CONTEXTUAL_SEVERITIES.get(rule_id, severity)


def adjustment_reason(finding, environment, single_broker, intelligence_context=None):
    rule_id = finding.get("rule_id")
    context_override = rule_context_override(intelligence_context, rule_id, environment)
    if context_override.get("reason"):
        return context_override["reason"]
    if context_override.get("severity"):
        return "Adjusted by organization intelligence context rule override " f"for {environment}."

    kafka_policy = kafka_environment_policy(intelligence_context, environment)
    if (
        rule_id == "kafka.cluster.broker_count.low"
        and kafka_policy.get("allow_single_broker") is True
    ):
        return (
            f"Downgraded because the {environment} intelligence context allows single-broker Kafka."
        )
    if (
        rule_id == "kafka.topic.replication_factor.low"
        and kafka_policy.get("allow_replication_factor_one") is True
    ):
        return f"Downgraded because the {environment} intelligence context allows replication factor 1."
    if (
        rule_id == "kafka.topic.partitions.low"
        and topic_context(intelligence_context, extract_entity_name(finding)).get(
            "low_partitions_allowed"
        )
        is True
    ):
        return "Downgraded because the matched topic pattern allows low partition count."
    if (
        rule_id == "kafka.topic.owner.missing"
        and kafka_policy.get("require_owner_metadata") is False
    ):
        return f"Downgraded because the {environment} intelligence context does not require owner metadata."

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
        if key == "kafka.topic_rf_low" and has_group(grouped, "kafka.single_broker_cluster"):
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
                "business_category": group_def.get(
                    "business_category", business_category_for(categories[key])
                ),
                "examples": [item for item in examples[key] if item],
                "recommendation": group_def["recommendation"],
                "remediation_command": group_def.get("remediation_command"),
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
            "business_category": risk["business_category"],
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
    return min(severities or ["INFO"], key=lambda severity: SEVERITY_ORDER.get(severity, 99))


def has_group(grouped, key):
    return key in grouped


def calculate_risk_points(findings):
    return sum(RISK_POINTS.get(finding.get("severity"), 0) for finding in findings)


def readiness_score_from_points(risk_points):
    return max(0, 100 - min(100, round(risk_points / 2)))


def business_category_for(category):
    return BUSINESS_CATEGORIES.get(category, "Governance")


def build_business_categories(score_findings, grouped_risks):
    categories = {
        name: {"risk": "LOW RISK", "findings": 0, "risk_points": 0}
        for name in (
            "Availability",
            "Security",
            "Capacity",
            "Governance",
            "Performance",
        )
    }

    grouped_keys = {risk["key"] for risk in grouped_risks}
    for risk in grouped_risks:
        category = risk["business_category"]
        categories.setdefault(category, {"risk": "LOW RISK", "findings": 0, "risk_points": 0})
        categories[category]["findings"] += 1
        categories[category]["risk_points"] += RISK_POINTS.get(risk["severity"], 0)

    for finding in score_findings:
        if finding.get("rule_id") in grouped_keys or finding.get("severity") == "INFO":
            continue
        category = finding.get("business_category") or business_category_for(
            finding.get("category")
        )
        categories.setdefault(category, {"risk": "LOW RISK", "findings": 0, "risk_points": 0})
        categories[category]["findings"] += 1
        categories[category]["risk_points"] += RISK_POINTS.get(finding.get("severity"), 0)

    for data in categories.values():
        data["risk"] = risk_from_points(data["risk_points"])

    return categories


def risk_from_points(points):
    if points >= 100:
        return "CRITICAL RISK"
    if points >= 50:
        return "HIGH RISK"
    if points >= 20:
        return "MEDIUM RISK"
    return "LOW RISK"


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
