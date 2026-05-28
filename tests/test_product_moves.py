from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.runtime_advisor import evaluate_kafka_runtime


def test_readiness_handles_runtime_stability_category():
    findings = [
        {
            "rule_id": "kafka.runtime.diagnostic",
            "domain": "kafka",
            "category": "runtime_stability",
            "severity": "HIGH",
            "title": "Kafka consumer lag is increasing",
            "impact": "Runtime degradation is possible.",
            "recommendation": "Investigate consumer processing latency.",
            "file": "runtime-kafka",
            "evidence": {"total_lag": 100000},
            "tags": [],
        }
    ]

    summary = calculate_readiness(findings)

    assert summary["categories"]["runtime_stability"]["findings"] == 1
    assert summary["high"] == 1


def test_runtime_findings_include_evidence_and_confidence():
    findings = evaluate_kafka_runtime(
        {
            "broker_disk_usage_percent": 84,
            "disk_growth_percent_7d": 22,
            "retention_bytes_configured": False,
            "cleanup_policy_configured": False,
            "producer_rate_increased": True,
            "consumer_lag_increasing": True,
            "avg_message_size_increased": True,
            "under_replicated_partitions": 0,
            "broker_count": 3,
            "partition_count": 420,
            "replication_factor": 3,
        },
        "runtime.yaml",
    )

    assert findings
    assert all(finding["evidence"] for finding in findings)
    assert all(finding.get("confidence") for finding in findings)


def test_readiness_static_applies_policy(monkeypatch):
    from beacon import cli

    raw_findings = [
        {
            "rule_id": "kafka.topic.retention_bytes.missing",
            "domain": "kafka",
            "category": "storage_sustainability",
            "severity": "HIGH",
            "title": "Kafka topic does not define retention_bytes",
            "impact": "Disk usage can grow unpredictably.",
            "recommendation": "Set retention_bytes.",
            "file": "kafka.yaml",
            "evidence": {"topic": "payments"},
            "tags": [],
        }
    ]
    captured = {}

    monkeypatch.setattr(cli, "scan_path", lambda path: raw_findings)
    monkeypatch.setattr(
        cli,
        "load_policy",
        lambda: {"kafka.topic.retention_bytes.missing": {"enabled": False}},
    )
    monkeypatch.setattr(cli, "print_readiness_summary", lambda summary: None)

    def capture_report(findings, **kwargs):
        captured["findings"] = findings
        captured["readiness_summary"] = kwargs["readiness_summary"]

    monkeypatch.setattr(cli, "print_report", capture_report)

    cli.readiness_static("infra", html=False, open_report=False, output="json")

    assert captured["findings"] == []
    assert captured["readiness_summary"]["score"] == 100


def test_live_kafka_topics_use_normalized_evaluator(monkeypatch):
    from beacon import kafka_runtime_connector

    captured = {}

    class FakePartition:
        replicas = [1, 2, 3]

    class FakeTopic:
        partitions = {0: FakePartition(), 1: FakePartition(), 2: FakePartition()}

    class FakeMetadata:
        brokers = {1: object(), 2: object(), 3: object()}
        topics = {"payments": FakeTopic()}

    class FakeFuture:
        def result(self, timeout=None):
            return {}

    class FakeAdminClient:
        def __init__(self, config):
            self.config = config

        def list_topics(self, timeout=None):
            return FakeMetadata()

        def describe_configs(self, resources):
            return {resource: FakeFuture() for resource in resources}

    def capture_evaluate(resources, context=None):
        captured["resource_types"] = [resource.type for resource in resources]
        captured["context"] = context
        return []

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", FakeAdminClient)
    monkeypatch.setattr(kafka_runtime_connector, "evaluate", capture_evaluate)
    monkeypatch.setattr(
        kafka_runtime_connector, "analyze_consumer_group_lag", lambda **kwargs: []
    )

    kafka_runtime_connector.analyze_kafka_cluster("localhost:9092")

    assert captured["resource_types"] == ["kafka_topic"]
    assert captured["context"] == {"file": "runtime-kafka"}


def test_scanner_uses_normalized_terraform_resources():
    from beacon.scanner import scan_file

    findings = scan_file("./examples/bad-infra/main.tf")

    assert any(
        finding["rule_id"] == "object_storage.public_access.enabled"
        for finding in findings
    )


def test_kafka_normalizer_accepts_nested_kafka_document():
    from beacon.rules import evaluate_kafka_config

    findings = evaluate_kafka_config(
        {
            "kafka": {
                "topics": [
                    {
                        "name": "payments",
                        "replication_factor": 1,
                        "partitions": 1,
                    }
                ]
            }
        },
        "kafka.yaml",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert "kafka.topic.partitions.low" in rule_ids


def test_direct_server_config_validation_fails_before_connect(monkeypatch):
    from beacon import kafka_runtime_connector

    def fail_if_called(config):
        raise AssertionError("AdminClient should not be constructed")

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", fail_if_called)

    findings = kafka_runtime_connector.analyze_kafka_cluster(
        bootstrap_server="localhost:9092",
        security_protocol="BAD_PROTOCOL",
    )

    assert any(
        finding["rule_id"] == "kafka.runtime.server_config.invalid"
        for finding in findings
    )
    assert not any(
        finding["rule_id"] == "kafka.runtime.connection.failed" for finding in findings
    )


def test_runtime_info_findings_do_not_reduce_score():
    from beacon.reporter import calculate_score

    findings = [
        {
            "rule_id": "kafka.runtime.read_only_mode",
            "domain": "kafka",
            "category": "runtime_stability",
            "severity": "INFO",
            "title": "Read-only mode",
            "impact": "No mutation will be performed.",
            "recommendation": "No action required.",
            "file": "runtime-kafka",
            "evidence": {"mode": "read_only"},
            "tags": [],
        }
    ]

    assert calculate_score(findings) == 100


def test_runtime_snapshot_uses_stable_rule_ids():
    from beacon.runtime_advisor import evaluate_kafka_runtime

    findings = evaluate_kafka_runtime(
        {
            "broker_disk_usage_percent": 91,
            "retention_bytes_configured": False,
            "cleanup_policy_configured": False,
        },
        "runtime.yaml",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "runtime.snapshot.diagnostic" not in rule_ids
    assert "kafka.runtime.disk_usage.critical" in rule_ids
    assert "kafka.runtime.decision.capacity_protection" in rule_ids


def test_runtime_rules_are_listed_in_registry():
    from beacon import rules_registry

    rules_registry.reload()
    rules = rules_registry.list_rules()

    assert "kafka.runtime.server_config.invalid" in rules
    assert "kafka.consumer_group.lag.high" in rules
    assert "kafka.runtime.decision.workload_investigation" in rules


def test_readiness_error_forces_not_ready():
    from beacon.readiness.kafka.readiness_engine import calculate_readiness

    summary = calculate_readiness(
        [
            {
                "rule_id": "kafka.runtime.server_config.invalid",
                "domain": "kafka",
                "category": "runtime_stability",
                "severity": "ERROR",
                "title": "Kafka direct server configuration is invalid",
                "impact": "Cannot start live readiness analysis.",
                "recommendation": "Fix config.",
                "file": "runtime-kafka",
                "evidence": {"field": "security_protocol"},
                "tags": [],
            }
        ]
    )

    assert summary["error"] == 1
    assert summary["production_decision"] == "NOT READY"
    assert summary["survivability"] == "ANALYSIS BLOCKED"
    assert "Resolve analysis errors" in summary["recommended_action"]
