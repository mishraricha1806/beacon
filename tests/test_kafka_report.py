from beacon.kafka_report import build_kafka_report
from beacon.readiness.kafka.readiness_engine import calculate_readiness


def kafka_finding(rule_id, title, severity="HIGH", tags=None):
    return {
        "rule_id": rule_id,
        "domain": "kafka",
        "category": "operational_safety",
        "severity": severity,
        "title": title,
        "impact": title,
        "recommendation": "fix it",
        "file": "kafka.yaml",
        "evidence": {},
        "tags": tags or [],
    }


def test_kafka_report_groups_findings_by_operational_area():
    report = build_kafka_report(
        [
            kafka_finding(
                "kafka.broker.security.plaintext_listener",
                "Kafka plaintext listener configured",
            ),
            kafka_finding(
                "kafka.consumer_group.lag.high",
                "High Kafka consumer lag detected",
            ),
            kafka_finding(
                "schema_registry.subject.compatibility.unsafe",
                "Schema subject has unsafe compatibility",
            ),
            kafka_finding(
                "kafka.history.rebalance_churn.high",
                "Kafka rebalance churn is high",
            ),
        ]
    )

    section_keys = {section["key"] for section in report["sections"]}

    assert "security_access" in section_keys
    assert "consumer_lag" in section_keys
    assert "schema_safety" in section_keys
    assert "trend_churn" in section_keys
    assert report["finding_count"] == 4


def test_readiness_summary_includes_kafka_report():
    summary = calculate_readiness(
        [
            kafka_finding(
                "kafka.broker.security.allow_everyone_if_no_acl",
                "Kafka broker allows access when no ACL is found",
                severity="CRITICAL",
            )
        ]
    )

    assert summary["kafka_report"]["title"] == "Kafka Operational Readiness"
    assert summary["kafka_report"]["sections"][0]["key"] == "security_access"


def test_kafka_report_prefers_specific_sections_over_generic_keywords():
    report = build_kafka_report(
        [
            kafka_finding(
                "kafka.topic.retention_bytes.missing",
                "Kafka topic does not define retention bytes",
            ),
            kafka_finding(
                "kafka.topic.schema_compatibility.unsafe",
                "Kafka topic has unsafe schema compatibility",
            ),
            kafka_finding(
                "kafka.producer.acks.unsafe",
                "Kafka producer has unsafe acks",
            ),
        ]
    )

    locations = {
        finding["rule_id"]: section["key"]
        for section in report["sections"]
        for finding in section["top_findings"]
    }

    assert locations["kafka.topic.retention_bytes.missing"] == "topic_safety"
    assert locations["kafka.topic.schema_compatibility.unsafe"] == "schema_safety"
    assert locations["kafka.producer.acks.unsafe"] == "recovery_replay"
