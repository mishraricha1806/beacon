import yaml

from beacon.intelligence.context import (
    load_intelligence_context,
    service_matching_aliases,
    service_matching_patterns,
)
from beacon.readiness.kafka.readiness_engine import calculate_readiness


def finding(rule_id, severity="CRITICAL", topic="claims.retry"):
    return {
        "rule_id": rule_id,
        "domain": "kafka",
        "category": "resiliency",
        "severity": severity,
        "title": f"Kafka topic '{topic}' has a production-readiness risk",
        "impact": "impact",
        "recommendation": "recommendation",
        "file": "runtime-kafka",
        "evidence": {"topic": topic},
        "tags": [],
    }


def test_intelligence_context_sets_environment_and_adjusts_kafka_policy(tmp_path):
    path = tmp_path / "context.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "organization": {"name": "Acme Platform", "environment": "dev"},
                "kafka_policy": {
                    "dev": {
                        "allow_replication_factor_one": True,
                        "allow_single_broker": True,
                    }
                },
            }
        )
    )

    context = load_intelligence_context(str(path))
    summary = calculate_readiness(
        [finding("kafka.topic.replication_factor.low")],
        intelligence_context=context,
    )

    assert summary["environment"] == "dev"
    assert summary["intelligence_context"]["loaded"] is True
    assert summary["intelligence_context"]["organization"] == "Acme Platform"
    assert summary["critical"] == 0
    assert summary["info"] == 1
    assert (
        "intelligence context allows replication factor 1"
        in summary["interpreted_findings"][0]["severity_adjustment_reason"]
    )


def test_intelligence_context_topic_patterns_adjust_low_partition_findings():
    context = {
        "environment": "prod",
        "topic_patterns": {
            "*.retry": {
                "low_partitions_allowed": True,
                "severity": "INFO",
            }
        },
    }

    summary = calculate_readiness(
        [
            finding(
                "kafka.topic.partitions.low",
                severity="HIGH",
                topic="claims.retry",
            )
        ],
        intelligence_context=context,
    )

    interpreted = summary["interpreted_findings"][0]

    assert summary["environment"] == "prod"
    assert interpreted["severity"] == "INFO"
    assert "topic pattern allows low partition count" in interpreted["severity_adjustment_reason"]


def test_intelligence_context_rule_override_is_deterministic():
    context = {
        "environment": "prod",
        "rule_overrides": {
            "kafka.topic.max_message_bytes.large": {
                "severity": "MEDIUM",
                "reason": "Large payloads are accepted for this isolated archive topic.",
            }
        },
    }

    summary = calculate_readiness(
        [
            finding(
                "kafka.topic.max_message_bytes.large",
                severity="HIGH",
                topic="archive.complete",
            )
        ],
        intelligence_context=context,
    )

    interpreted = summary["interpreted_findings"][0]

    assert interpreted["severity"] == "MEDIUM"
    assert (
        interpreted["severity_adjustment_reason"]
        == "Large payloads are accepted for this isolated archive topic."
    )


def test_intelligence_context_exposes_service_matching_aliases():
    context = {
        "service_matching": {
            "aliases": {
                "checkout": ["claim-intake-edge", "member-enrollment-flow"],
            }
        }
    }

    aliases = service_matching_aliases(context)

    assert aliases["checkout"] == ["claim-intake-edge", "member-enrollment-flow"]


def test_intelligence_context_exposes_service_matching_patterns():
    context = {
        "service_matching": {
            "patterns": {
                "claims-*-consumer": "claims-platform",
            }
        }
    }

    patterns = service_matching_patterns(context)

    assert patterns["claims-*-consumer"] == "claims-platform"
