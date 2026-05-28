from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kafka_config
import beacon.rules.kafka_registered_rules  # noqa: F401


def test_rule_engine_detects_kafka_replication_factor_low():
    data = {
        "topics": [
            {
                "name": "payments",
                "replication_factor": 1,
                "partitions": 3,
            }
        ]
    }

    resources = normalize_kafka_config(data, "examples/kafka.yaml")
    findings = evaluate(resources, context={"file": "examples/kafka.yaml"})

    assert any(
        finding["rule_id"] == "kafka.topic.replication_factor.low"
        for finding in findings
    )

    finding = next(
        finding
        for finding in findings
        if finding["rule_id"] == "kafka.topic.replication_factor.low"
    )

    assert finding["evidence"]["topic"] == "payments"
    assert finding["evidence"]["replication_factor"] == 1
