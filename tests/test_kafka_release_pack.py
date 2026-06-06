from pathlib import Path


ROOT = Path("examples/supported/kafka")


def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def test_kafka_release_docs_exist():
    doc = Path("docs/KAFKA_RELEASE.md")

    assert doc.exists()
    text = doc.read_text()

    assert "Supported Inputs" in text
    assert "Offline ACL Exports" in text
    assert "Kafka History" in text
    assert "Scenario Pack" in text
    assert "Known Limits" in text


def test_kafka_scenario_pack_unsafe_security():
    from beacon.scanner import scan_file

    findings = scan_file(str(ROOT / "scenarios" / "unsafe-security.yaml"))
    ids = rule_ids(findings)

    assert "kafka.broker.security.plaintext_listener" in ids
    assert "kafka.broker.security.allow_everyone_if_no_acl" in ids
    assert "kafka.broker.client_quotas.missing" in ids


def test_kafka_scenario_pack_unsafe_acls():
    from beacon.kafka_acl_scanner import analyze_kafka_acl_file

    findings = analyze_kafka_acl_file(str(ROOT / "scenarios" / "unsafe-acls.yaml"))

    assert findings[0]["rule_id"] == "kafka.acl.export.broad_allow"


def test_kafka_scenario_pack_lag_rebalance_history():
    from beacon.kafka_history import analyze_kafka_history_file

    findings = analyze_kafka_history_file(str(ROOT / "scenarios" / "lag-rebalance-history.yaml"))
    ids = rule_ids(findings)

    assert "kafka.history.consumer_lag.growing" in ids
    assert "kafka.history.producer_rate.increased" in ids
    assert "kafka.history.deployment_correlated_lag" in ids
    assert "kafka.history.controller_churn.high" in ids
    assert "kafka.history.rebalance_churn.high" in ids
    assert "kafka.history.consumer_group.member_churn" in ids


def test_kafka_scenario_pack_schema_poison_risk():
    from beacon.scanner import scan_file

    findings = scan_file(str(ROOT / "scenarios" / "schema-poison-risk.yaml"))
    ids = rule_ids(findings)

    assert "kafka.topic.schema_compatibility.unsafe" in ids
    assert "kafka.producer.acks.unsafe" in ids
    assert "kafka.consumer.auto_commit.enabled" in ids
    assert "kafka.consumer.dlq.missing" in ids
