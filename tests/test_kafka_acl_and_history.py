def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def test_kafka_acl_export_detects_broad_allow(tmp_path):
    from beacon.kafka_acl_scanner import analyze_kafka_acl_file

    path = tmp_path / "acls.yaml"
    path.write_text(
        """
kafka_acls:
  - principal: User:*
    host: "*"
    operation: ALL
    permission_type: ALLOW
    resource_type: TOPIC
    resource_name: "*"
    resource_pattern_type: LITERAL
"""
    )

    findings = analyze_kafka_acl_file(str(path))

    assert findings[0]["rule_id"] == "kafka.acl.export.broad_allow"
    assert findings[0]["severity"] == "HIGH"


def test_kafka_acl_export_inspected_when_scoped(tmp_path):
    from beacon.kafka_acl_scanner import analyze_kafka_acl_file

    path = tmp_path / "acls.yaml"
    path.write_text(
        """
acls:
  - principal: User:payments-service
    host: "*"
    operation: READ
    permission_type: ALLOW
    resource_type: TOPIC
    resource_name: payments
    resource_pattern_type: LITERAL
"""
    )

    findings = analyze_kafka_acl_file(str(path))

    assert findings[0]["rule_id"] == "kafka.acl.export.inspected"


def test_kafka_history_detects_worsening_trends(tmp_path):
    from beacon.kafka_history import analyze_kafka_history_file

    path = tmp_path / "history.yaml"
    path.write_text(
        """
kafka_history:
  - timestamp: "2026-05-31T09:00:00Z"
    broker_disk_usage_percent: 70
    total_consumer_lag: 10000
    consumer_groups:
      - group_id: payments
        members: [a]
  - timestamp: "2026-05-31T09:10:00Z"
    broker_disk_usage_percent: 82
    total_consumer_lag: 90000
    consumer_groups:
      - group_id: payments
        members: [b]
  - timestamp: "2026-05-31T09:20:00Z"
    broker_disk_usage_percent: 86
    total_consumer_lag: 140000
    controller_change_count_15m: 3
    rebalance_count_15m: 4
    consumer_groups:
      - group_id: payments
        members: [c, d]
"""
    )

    ids = rule_ids(analyze_kafka_history_file(str(path)))

    assert "kafka.history.disk_usage.growing" in ids
    assert "kafka.history.consumer_lag.growing" in ids
    assert "kafka.history.controller_churn.high" in ids
    assert "kafka.history.rebalance_churn.high" in ids
    assert "kafka.history.consumer_group.member_churn" in ids


def test_kafka_history_requires_multiple_snapshots(tmp_path):
    from beacon.kafka_history import analyze_kafka_history_file

    path = tmp_path / "history.yaml"
    path.write_text("kafka_history:\n  - broker_disk_usage_percent: 70\n")

    findings = analyze_kafka_history_file(str(path))

    assert findings[0]["rule_id"] == "kafka.history.insufficient_snapshots"
