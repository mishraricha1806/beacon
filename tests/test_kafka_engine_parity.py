from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kafka_config

import beacon.rules.kafka_registered_rules  # noqa: F401

from beacon.rules import evaluate_kafka_config


def test_kafka_engine_parity():
    data = {
        "topics": [
            {
                "name": "payments",
                "replication_factor": 1,
                "partitions": 1,
                "retention_ms": 3600000,
            }
        ]
    }

    facade_findings = evaluate_kafka_config(
        data,
        "examples/test.yaml",
    )

    resources = normalize_kafka_config(
        data,
        "examples/test.yaml",
    )

    new_findings = evaluate(
        resources,
        context={"file": "examples/test.yaml"},
    )

    facade_rule_ids = {f["rule_id"] for f in facade_findings}
    new_rule_ids = {f["rule_id"] for f in new_findings}

    assert facade_rule_ids.issubset(new_rule_ids)
