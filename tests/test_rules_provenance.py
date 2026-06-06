from beacon.rules import evaluate_kafka_config, evaluate_terraform_config


def test_kafka_replication_rule_includes_rule_id_and_evidence():
    data = {
        "topics": [
            {
                "name": "payments",
                "replication_factor": 1,
                "partitions": 3,
                "retention_ms": 86400000,
                "retention_bytes": 1000000,
            }
        ]
    }

    findings = evaluate_kafka_config(data, "examples/kafka-topics.yaml")

    assert any(f.get("rule_id") == "kafka.topic.replication_factor.low" for f in findings)

    f = next(f for f in findings if f.get("rule_id") == "kafka.topic.replication_factor.low")
    assert "evidence" in f
    assert f["evidence"]["topic"] == "payments"
    assert f["evidence"]["replication_factor"] == 1


def test_kafka_retention_bytes_missing_includes_rule_id_and_evidence():
    data = {
        "topics": [
            {
                "name": "payments",
                "replication_factor": 3,
                "partitions": 3,
                # retention_bytes intentionally missing
            }
        ]
    }

    findings = evaluate_kafka_config(data, "examples/kafka-topics.yaml")

    assert any(f.get("rule_id") == "kafka.topic.retention_bytes.missing" for f in findings)

    f = next(f for f in findings if f.get("rule_id") == "kafka.topic.retention_bytes.missing")
    assert "evidence" in f
    assert f["evidence"]["topic"] == "payments"
    assert "retention_bytes" in f["evidence"]


def test_terraform_s3_public_access_includes_offending_keys_and_rule_id():
    data = {
        "resource": [
            {
                "aws_s3_bucket_public_access_block": {
                    "payments_block": {
                        "block_public_acls": False,
                        "block_public_policy": True,
                        "ignore_public_acls": True,
                        "restrict_public_buckets": False,
                    }
                }
            }
        ]
    }

    findings = evaluate_terraform_config(data, "examples/main.tf")

    assert any(f.get("rule_id") == "object_storage.public_access.enabled" for f in findings)

    f = next(f for f in findings if f.get("rule_id") == "object_storage.public_access.enabled")
    assert "evidence" in f
    assert "offending_keys" in f["evidence"]
    assert set(f["evidence"]["offending_keys"]) == {
        "block_public_acls",
        "restrict_public_buckets",
    }
