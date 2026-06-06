from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kafka_config
import beacon.rules.kafka_registered_rules  # noqa: F401


def test_rule_engine_detects_unbounded_retention():
    data = {
        "topics": [
            {
                "name": "logs",
                "replication_factor": 3,
                "partitions": 3,
                "retention_ms": -1,
            }
        ]
    }

    resources = normalize_kafka_config(data, "examples/kafka.yaml")
    findings = evaluate(resources, context={"file": "examples/kafka.yaml"})

    assert any(finding["rule_id"] == "kafka.topic.retention_ms.unbounded" for finding in findings)
