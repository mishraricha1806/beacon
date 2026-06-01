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


def test_readiness_groups_repeated_kafka_topic_findings_for_nonprod():
    findings = [
        {
            "rule_id": "kafka.cluster.broker_count.low",
            "domain": "kafka",
            "category": "resiliency",
            "severity": "HIGH",
            "title": "Kafka cluster has only 1 broker(s)",
            "impact": "Low broker count.",
            "recommendation": "Use more brokers.",
            "file": "runtime-kafka",
            "evidence": {"cluster": "cirrus-kafka-nonprod-gcp"},
            "tags": [],
        }
    ]

    for topic in ("claims.response", "finance.feedback", "member.events"):
        findings.extend(
            [
                {
                    "rule_id": "kafka.topic.replication_factor.low",
                    "domain": "kafka",
                    "category": "resiliency",
                    "severity": "CRITICAL",
                    "title": f"Kafka topic '{topic}' has replication factor 1",
                    "impact": "Broker failure can interrupt workflows.",
                    "recommendation": "Use replication_factor=3.",
                    "file": "runtime-kafka",
                    "evidence": {"topic": topic},
                    "tags": [],
                },
                {
                    "rule_id": "kafka.topic.partitions.low",
                    "domain": "kafka",
                    "category": "scalability",
                    "severity": "HIGH",
                    "title": f"Kafka topic '{topic}' has low partition count",
                    "impact": "Low partitions can limit parallelism.",
                    "recommendation": "Use more partitions.",
                    "file": "runtime-kafka",
                    "evidence": {"topic": topic},
                    "tags": [],
                },
            ]
        )

    summary = calculate_readiness(findings)

    assert summary["environment"] == "nonprod"
    assert summary["critical"] == 0
    assert summary["raw_critical"] == 3
    assert summary["grouped_risks"][0]["severity"] in {"LOW", "INFO"}
    assert any(
        risk["key"] == "kafka.topic_rf_low" and risk["affected_count"] == 3
        for risk in summary["grouped_risks"]
    )
    assert summary["suppressed_duplicate_count"] > 0


def test_readiness_uses_weighted_group_scoring_and_business_categories():
    findings = [
        {
            "rule_id": "kafka.topic.max_message_bytes.large",
            "domain": "kafka",
            "category": "storage_sustainability",
            "severity": "HIGH",
            "title": "Kafka topic 'claims.response' allows messages larger than 1MB",
            "impact": "Large messages increase broker disk I/O.",
            "recommendation": "Keep messages small.",
            "file": "runtime-kafka",
            "evidence": {"topic": "claims.response"},
            "tags": [],
        },
        {
            "rule_id": "kafka.topic.max_message_bytes.large",
            "domain": "kafka",
            "category": "storage_sustainability",
            "severity": "HIGH",
            "title": "Kafka topic 'finance.feedback' allows messages larger than 1MB",
            "impact": "Large messages increase broker disk I/O.",
            "recommendation": "Keep messages small.",
            "file": "runtime-kafka",
            "evidence": {"topic": "finance.feedback"},
            "tags": [],
        },
        {
            "rule_id": "kafka.topic.retention_ms.unbounded",
            "domain": "kafka",
            "category": "storage_sustainability",
            "severity": "HIGH",
            "title": "Kafka topic 'archive.complete' has unbounded retention",
            "impact": "Unbounded retention can cause disk growth.",
            "recommendation": "Set retention.",
            "file": "runtime-kafka",
            "evidence": {"topic": "archive.complete"},
            "tags": [],
        },
    ]

    summary = calculate_readiness(findings, environment="dev")

    assert summary["environment"] == "dev"
    assert summary["risk_points"] == 100
    assert summary["score"] == 50
    assert summary["business_categories"]["Capacity"]["risk_points"] == 100
    assert summary["business_categories"]["Capacity"]["risk"] == "CRITICAL RISK"
    assert any(
        risk["key"] == "kafka.large_messages"
        and risk["affected_count"] == 2
        and risk["business_category"] == "Capacity"
        and "kafka-configs" in risk["remediation_command"]
        for risk in summary["grouped_risks"]
    )


def test_readiness_environment_profile_controls_kafka_ha_severity():
    finding = {
        "rule_id": "kafka.topic.replication_factor.low",
        "domain": "kafka",
        "category": "resiliency",
        "severity": "CRITICAL",
        "title": "Kafka topic 'claims.response' has replication factor 1",
        "impact": "Broker failure can interrupt workflows.",
        "recommendation": "Use replication_factor=3.",
        "file": "runtime-kafka",
        "evidence": {"topic": "claims.response"},
        "tags": [],
    }

    dev_summary = calculate_readiness([finding], environment="dev")
    prod_summary = calculate_readiness([finding], environment="prod")

    assert dev_summary["critical"] == 0
    assert dev_summary["info"] == 1
    assert prod_summary["critical"] == 1
    assert prod_summary["production_decision"] == "NOT READY"


def test_readiness_top_reasons_follow_severity_order():
    findings = [
        {
            "rule_id": "low.rule",
            "domain": "kafka",
            "category": "operational_safety",
            "severity": "LOW",
            "title": "Low item",
            "impact": "impact",
            "recommendation": "recommendation",
            "file": "x",
            "evidence": {},
            "tags": [],
        },
        {
            "rule_id": "critical.rule",
            "domain": "kafka",
            "category": "operational_safety",
            "severity": "CRITICAL",
            "title": "Critical item",
            "impact": "impact",
            "recommendation": "recommendation",
            "file": "x",
            "evidence": {},
            "tags": [],
        },
        {
            "rule_id": "high.rule",
            "domain": "kafka",
            "category": "operational_safety",
            "severity": "HIGH",
            "title": "High item",
            "impact": "impact",
            "recommendation": "recommendation",
            "file": "x",
            "evidence": {},
            "tags": [],
        },
    ]

    summary = calculate_readiness(findings)

    assert summary["top_reasons"][0].startswith("CRITICAL")
    assert summary["top_reasons"][1].startswith("HIGH")
    assert summary["top_reasons"][2].startswith("LOW")


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


def test_all_domain_collector_includes_static_runtime_and_live_inputs(monkeypatch):
    from beacon import cli

    calls = []

    def finding(rule_id, domain):
        return {
            "rule_id": rule_id,
            "domain": domain,
            "category": "runtime_stability",
            "severity": "HIGH",
            "title": rule_id,
            "impact": "impact",
            "recommendation": "recommendation",
            "file": domain,
            "evidence": {},
            "tags": [],
        }

    monkeypatch.setattr(
        cli,
        "scan_path",
        lambda path: calls.append(("static", path))
        or [finding("static.rule", "static")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_runtime_snapshot_file",
        lambda path: calls.append(("snapshot", path))
        or [finding("snapshot.rule", "snapshot")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_flow_file",
        lambda path: calls.append(("flow", path)) or [finding("flow.rule", "flow")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_prometheus_config",
        lambda path, timeout=5: calls.append(("prometheus", path, timeout))
        or [finding("prometheus.rule", "prometheus")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_opentelemetry_file",
        lambda path: calls.append(("opentelemetry", path))
        or [finding("opentelemetry.rule", "opentelemetry")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_schema_registry_config",
        lambda path, timeout=5: calls.append(("schema-registry", path, timeout))
        or [finding("schema_registry.rule", "kafka")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_kafka_acl_file",
        lambda path: calls.append(("kafka-acls", path))
        or [finding("kafka.acl.rule", "kafka")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_kafka_history_file",
        lambda path: calls.append(("kafka-history", path))
        or [finding("kafka.history.rule", "kafka")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_kafka_cluster",
        lambda **kwargs: calls.append(("kafka", kwargs))
        or [finding("kafka.rule", "kafka")],
    )
    monkeypatch.setattr(
        cli,
        "analyze_kubernetes_cluster",
        lambda **kwargs: calls.append(("kubernetes", kwargs))
        or [finding("kubernetes.rule", "kubernetes")],
    )

    findings = cli.collect_all_domain_findings(
        static_path="infra",
        snapshot_path="runtime.yaml",
        flow_path="flow.yaml",
        prometheus_path="prom.yaml",
        opentelemetry_path="otel.yaml",
        schema_registry_path="schema-registry.yaml",
        kafka_acl_path="acls.yaml",
        kafka_history_path="history.yaml",
        prometheus_timeout=2,
        schema_registry_timeout=3,
        kafka_bootstrap_server="localhost:9092",
        kafka_churn_samples=3,
        kafka_churn_interval_seconds=0.25,
        kubernetes_live=True,
        kubernetes_namespace="payments",
    )

    rule_ids = {item["rule_id"] for item in findings}

    assert rule_ids == {
        "static.rule",
        "snapshot.rule",
        "flow.rule",
        "prometheus.rule",
        "opentelemetry.rule",
        "schema_registry.rule",
        "kafka.acl.rule",
        "kafka.history.rule",
        "kafka.rule",
        "kubernetes.rule",
    }
    assert ("prometheus", "prom.yaml", 2) in calls
    assert ("schema-registry", "schema-registry.yaml", 3) in calls
    assert ("kafka-acls", "acls.yaml") in calls
    assert ("kafka-history", "history.yaml") in calls
    kafka_call = next(call for call in calls if call[0] == "kafka")
    assert kafka_call[1]["churn_samples"] == 3
    assert kafka_call[1]["churn_interval_seconds"] == 0.25
    assert any(call[0] == "kubernetes" for call in calls)


def test_readiness_all_emits_readiness_summary(monkeypatch):
    from beacon import cli

    captured = {}

    monkeypatch.setattr(
        cli,
        "collect_all_domain_findings",
        lambda **kwargs: [
            {
                "rule_id": "api.runtime.retry_amplification",
                "domain": "api",
                "category": "runtime_stability",
                "severity": "CRITICAL",
                "title": "API retry amplification",
                "impact": "impact",
                "recommendation": "recommendation",
                "file": "snapshot",
                "evidence": {},
                "tags": [],
            }
        ],
    )
    monkeypatch.setattr(cli, "load_policy", lambda: {})
    monkeypatch.setattr(
        cli, "apply_policy_to_findings", lambda findings, policy: findings
    )
    monkeypatch.setattr(
        cli,
        "print_readiness_summary",
        lambda summary: captured.setdefault("summary", summary),
    )
    monkeypatch.setattr(
        cli,
        "print_report",
        lambda findings, **kwargs: captured.update({"findings": findings, **kwargs}),
    )

    cli.readiness_all(
        static_path="infra",
        html=False,
        open_report=False,
        output="json",
    )

    assert captured["summary"]["production_decision"] == "NOT READY"
    assert captured["readiness_summary"] == captured["summary"]
    assert captured["findings"][0]["domain"] == "api"


def test_diagnose_all_emits_diagnostic_report_without_readiness_summary(monkeypatch):
    from beacon import cli

    captured = {}

    monkeypatch.setattr(
        cli,
        "collect_all_domain_findings",
        lambda **kwargs: [
            {
                "rule_id": "database.runtime.latency.high",
                "domain": "database",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "Database latency",
                "impact": "impact",
                "recommendation": "recommendation",
                "file": "snapshot",
                "evidence": {},
                "tags": [],
            }
        ],
    )
    monkeypatch.setattr(cli, "load_policy", lambda: {})
    monkeypatch.setattr(
        cli, "apply_policy_to_findings", lambda findings, policy: findings
    )
    monkeypatch.setattr(
        cli,
        "print_report",
        lambda findings, **kwargs: captured.update({"findings": findings, **kwargs}),
    )

    cli.diagnose_all(
        snapshot_path="runtime.yaml",
        html=False,
        open_report=False,
        output="json",
    )

    assert captured["findings"][0]["domain"] == "database"
    assert "readiness_summary" not in captured


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
        captured.setdefault("resource_types", []).extend(
            resource.type for resource in resources
        )
        captured["context"] = context
        return []

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", FakeAdminClient)
    monkeypatch.setattr(kafka_runtime_connector, "evaluate", capture_evaluate)
    monkeypatch.setattr(
        kafka_runtime_connector, "analyze_consumer_group_lag", lambda **kwargs: []
    )

    kafka_runtime_connector.analyze_kafka_cluster("localhost:9092")

    assert "kafka_topic" in captured["resource_types"]
    assert "kafka_broker_config" in captured["resource_types"]
    assert captured["context"] == {"file": "runtime-kafka"}


def test_live_kafka_consumer_group_filter_limits_topic_diagnostics(monkeypatch):
    from beacon import kafka_runtime_connector

    captured = {"topic_names": []}

    class FakePartition:
        replicas = [1, 2, 3]

    class FakeTopic:
        partitions = {0: FakePartition()}

    class FakeMetadata:
        brokers = {1: object(), 2: object(), 3: object()}
        topics = {
            "payments": FakeTopic(),
            "unrelated": FakeTopic(),
        }

    class FakeTopicPartition:
        topic = "payments"
        partition = 0
        offset = 10

    class FakeOffsetsResult:
        topic_partitions = [FakeTopicPartition()]

    class FakeFuture:
        def __init__(self, value=None):
            self.value = value or {}

        def result(self, timeout=None):
            return self.value

    class FakeAdminClient:
        def __init__(self, config):
            self.config = config

        def list_topics(self, timeout=None):
            return FakeMetadata()

        def describe_configs(self, resources):
            captured["topic_names"].extend(resource.name for resource in resources)
            return {resource: FakeFuture({}) for resource in resources}

        def list_consumer_group_offsets(self, requests, request_timeout=None):
            return {"payments-consumer": FakeFuture(FakeOffsetsResult())}

        def list_offsets(self, requests, request_timeout=None):
            return {
                topic_partition: FakeFuture(type("Offset", (), {"offset": 10})())
                for topic_partition in requests
            }

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", FakeAdminClient)
    monkeypatch.setattr(
        kafka_runtime_connector, "evaluate", lambda resources, context=None: []
    )
    monkeypatch.setattr(
        kafka_runtime_connector, "analyze_acl_posture", lambda admin_client: []
    )
    monkeypatch.setattr(
        kafka_runtime_connector,
        "describe_consumer_group_stability",
        lambda admin_client, group_ids: [],
    )
    monkeypatch.setattr(
        kafka_runtime_connector,
        "analyze_consumer_group_churn",
        lambda admin_client, group_ids, samples=1, interval_seconds=0: [],
    )

    findings = kafka_runtime_connector.analyze_kafka_cluster(
        "localhost:9092",
        consumer_group="payments-consumer",
    )

    assert "payments" in captured["topic_names"]
    assert "unrelated" not in captured["topic_names"]
    connection = next(
        finding
        for finding in findings
        if finding["rule_id"] == "kafka.runtime.connection.success"
    )
    assert connection["evidence"]["topic_scope"] == "consumer_group_committed_topics"
    assert connection["evidence"]["analyzed_topic_count"] == 1


def test_live_kafka_consumer_group_without_offsets_skips_cluster_topic_diagnostics(
    monkeypatch,
):
    from beacon import kafka_runtime_connector

    captured = {"topic_names": []}

    class FakePartition:
        replicas = [1, 2, 3]

    class FakeTopic:
        partitions = {0: FakePartition()}

    class FakeMetadata:
        brokers = {1: object(), 2: object(), 3: object()}
        topics = {"payments": FakeTopic(), "unrelated": FakeTopic()}

    class FakeOffsetsResult:
        topic_partitions = []

    class FakeFuture:
        def __init__(self, value=None):
            self.value = value or {}

        def result(self, timeout=None):
            return self.value

    class FakeAdminClient:
        def __init__(self, config):
            self.config = config

        def list_topics(self, timeout=None):
            return FakeMetadata()

        def describe_configs(self, resources):
            captured["topic_names"].extend(resource.name for resource in resources)
            return {}

        def list_consumer_group_offsets(self, requests, request_timeout=None):
            return {"payments-consumer": FakeFuture(FakeOffsetsResult())}

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", FakeAdminClient)
    monkeypatch.setattr(
        kafka_runtime_connector, "evaluate", lambda resources, context=None: []
    )
    monkeypatch.setattr(
        kafka_runtime_connector, "analyze_acl_posture", lambda admin_client: []
    )
    monkeypatch.setattr(
        kafka_runtime_connector,
        "describe_consumer_group_stability",
        lambda admin_client, group_ids: [],
    )
    monkeypatch.setattr(
        kafka_runtime_connector,
        "analyze_consumer_group_churn",
        lambda admin_client, group_ids, samples=1, interval_seconds=0: [],
    )

    findings = kafka_runtime_connector.analyze_kafka_cluster(
        "localhost:9092",
        consumer_group="payments-consumer",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "payments" not in captured["topic_names"]
    assert "unrelated" not in captured["topic_names"]
    assert "kafka.runtime.topic_scope.no_committed_offsets" in rule_ids
    connection = next(
        finding
        for finding in findings
        if finding["rule_id"] == "kafka.runtime.connection.success"
    )
    assert (
        connection["evidence"]["topic_scope"]
        == "consumer_group_only_no_committed_topics"
    )
    assert connection["evidence"]["analyzed_topic_count"] == 0


def test_live_kafka_partition_health_detects_replication_and_leader_risk():
    from types import SimpleNamespace

    from beacon.kafka_runtime_connector import build_partition_health_findings

    metadata = SimpleNamespace(
        brokers={
            1: SimpleNamespace(rack="az-a"),
            2: SimpleNamespace(rack="az-a"),
            3: SimpleNamespace(rack="az-a"),
        },
        topics={
            "payments": SimpleNamespace(
                partitions={
                    0: SimpleNamespace(leader=-1, replicas=[1, 2, 3], isrs=[1, 2]),
                    1: SimpleNamespace(leader=1, replicas=[1, 2, 3], isrs=[1]),
                    2: SimpleNamespace(leader=1, replicas=[1, 2, 3], isrs=[1, 2, 3]),
                    3: SimpleNamespace(leader=1, replicas=[1, 2, 3], isrs=[1, 2, 3]),
                }
            )
        },
    )

    findings = build_partition_health_findings(
        metadata=metadata,
        topic_names=["payments"],
        broker_count=3,
    )
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.cluster.offline_partitions" in rule_ids
    assert "kafka.cluster.under_replicated_partitions" in rule_ids
    assert "kafka.cluster.under_min_isr_partitions" in rule_ids
    assert "kafka.cluster.leader_imbalance.high" in rule_ids
    assert "kafka.cluster.replica_placement.single_failure_domain" in rule_ids


def test_live_kafka_consumer_group_stability_detects_rebalancing_and_empty():
    from types import SimpleNamespace

    from beacon.kafka_runtime_connector import build_consumer_group_stability_findings

    rebalancing = build_consumer_group_stability_findings(
        "payments-consumer",
        SimpleNamespace(state="PREPARING_REBALANCE", members=[object()]),
    )
    empty = build_consumer_group_stability_findings(
        "audit-consumer",
        SimpleNamespace(state="EMPTY", members=[]),
    )

    assert any(
        finding["rule_id"] == "kafka.consumer_group.rebalancing"
        for finding in rebalancing
    )
    assert any(finding["rule_id"] == "kafka.consumer_group.empty" for finding in empty)


def test_live_kafka_acl_posture_detects_broad_allow():
    from types import SimpleNamespace

    from beacon.kafka_runtime_connector import analyze_acl_posture

    class FakeFuture:
        def result(self, timeout=None):
            return [
                SimpleNamespace(
                    principal="User:*",
                    host="*",
                    operation="AclOperation.ALL",
                    permission_type="AclPermissionType.ALLOW",
                    restype="ResourceType.TOPIC",
                    name="*",
                    resource_pattern_type="ResourcePatternType.LITERAL",
                )
            ]

    class FakeAdminClient:
        def describe_acls(self, *args, **kwargs):
            return FakeFuture()

    findings = analyze_acl_posture(FakeAdminClient())

    assert findings[0]["rule_id"] == "kafka.runtime.acl.broad_allow"
    assert findings[0]["severity"] == "HIGH"


def test_live_kafka_client_quota_posture_detects_missing_and_configured():
    from beacon.kafka_runtime_connector import build_live_quota_findings

    missing = build_live_quota_findings(
        [
            {"id": "1", "producer_quota_bytes_per_second": None},
            {"id": "2", "consumer_quota_bytes_per_second": None},
        ]
    )
    configured = build_live_quota_findings(
        [
            {
                "id": "1",
                "producer_quota_bytes_per_second": 1048576,
                "consumer_quota_bytes_per_second": 1048576,
            }
        ]
    )

    assert missing[0]["rule_id"] == "kafka.runtime.client_quotas.missing"
    assert configured[0]["rule_id"] == "kafka.runtime.client_quotas.configured"


def test_live_kafka_consumer_group_churn_detects_member_changes(monkeypatch):
    from types import SimpleNamespace

    from beacon import kafka_runtime_connector

    samples = [
        {"payments": SimpleNamespace(members=[SimpleNamespace(member_id="a")])},
        {"payments": SimpleNamespace(members=[SimpleNamespace(member_id="b")])},
        {
            "payments": SimpleNamespace(
                members=[SimpleNamespace(member_id="b"), SimpleNamespace(member_id="c")]
            )
        },
    ]

    monkeypatch.setattr(
        kafka_runtime_connector,
        "describe_consumer_groups",
        lambda admin_client, group_ids: samples.pop(0),
    )

    findings = kafka_runtime_connector.analyze_consumer_group_churn(
        admin_client=object(),
        group_ids=["payments"],
        samples=3,
        interval_seconds=0,
    )

    assert findings[0]["rule_id"] == "kafka.consumer_group.member_churn.high"


def test_kafka_runtime_snapshot_v2_covers_production_instability_signals():
    from beacon.runtime_advisor import evaluate_kafka_runtime

    findings = evaluate_kafka_runtime(
        {
            "broker_disk_usage_percent": 88,
            "broker_disk_usage_by_broker": {"1": 94, "2": 62, "3": 60},
            "retention_bytes_configured": True,
            "cleanup_policy_configured": True,
            "consumer_lag_increasing": True,
            "consumer_group_state": "REBALANCING",
            "active_members": 0,
            "expected_members": 3,
            "rebalance_count_15m": 5,
            "producer_error_rate_percent": 7,
            "under_replicated_partitions": 2,
            "under_min_isr_partitions": 1,
            "offline_partitions": 1,
            "leader_imbalance_percent": 65,
            "active_controller_count": 2,
            "controller_change_count_15m": 3,
            "partition_reassignment_count": 4,
            "replication_fetcher_lag": 15000,
            "request_latency_p95_ms": 750,
            "request_queue_utilization_percent": 86,
            "network_io_utilization_percent": 91,
            "produce_throttle_time_ms": 140,
            "fetch_throttle_time_ms": 160,
            "schema_registry_available": False,
            "schema_incompatible_changes_24h": 2,
            "backlog_messages": 5000000,
            "consumer_throughput_messages_per_sec": 100,
            "producer_rate_messages_per_sec": 50,
            "replay_target_hours": 12,
            "retention_remaining_hours": 10,
            "broker_count": 3,
            "partition_count": 200,
            "replication_factor": 3,
        },
        "runtime.yaml",
    )
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.runtime.broker_disk_skew.critical" in rule_ids
    assert "kafka.runtime.broker_disk_skew.high" in rule_ids
    assert "kafka.runtime.offline_partitions" in rule_ids
    assert "kafka.runtime.under_min_isr_partitions" in rule_ids
    assert "kafka.runtime.leader_imbalance.high" in rule_ids
    assert "kafka.runtime.rebalance_storm" in rule_ids
    assert "kafka.runtime.consumer_group.unstable" in rule_ids
    assert "kafka.runtime.consumer_group.no_active_members" in rule_ids
    assert "kafka.runtime.consumer_group.member_shortfall" in rule_ids
    assert "kafka.runtime.producer_error_rate.high" in rule_ids
    assert "kafka.runtime.request_latency.high" in rule_ids
    assert "kafka.runtime.controller_count.invalid" in rule_ids
    assert "kafka.runtime.controller_churn.high" in rule_ids
    assert "kafka.runtime.partition_reassignment.active" in rule_ids
    assert "kafka.runtime.replication_fetcher_lag.high" in rule_ids
    assert "kafka.runtime.request_queue_saturation.high" in rule_ids
    assert "kafka.runtime.network_saturation.high" in rule_ids
    assert "kafka.runtime.producer_throttle.high" in rule_ids
    assert "kafka.runtime.fetch_throttle.high" in rule_ids
    assert "kafka.runtime.schema_registry.unavailable" in rule_ids
    assert "kafka.runtime.schema_incompatible_changes" in rule_ids
    assert "kafka.runtime.replay.time_exceeds_target" in rule_ids
    assert "kafka.runtime.replay.retention_window_insufficient" in rule_ids


def test_kafka_replay_detects_backlog_with_no_drain_capacity():
    from beacon.runtime_advisor import evaluate_kafka_runtime

    findings = evaluate_kafka_runtime(
        {
            "broker_disk_usage_percent": 70,
            "backlog_messages": 1000000,
            "consumer_throughput_messages_per_sec": 100,
            "producer_rate_messages_per_sec": 150,
            "replay_target_hours": 4,
        },
        "runtime.yaml",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.runtime.replay.no_drain_capacity" in rule_ids


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


def test_kafka_access_config_resolves_generic_profiles(tmp_path):
    from beacon.diagnose.kafka.access_config import (
        admin_config_from_profile,
        load_kafka_access_config,
    )

    ca = tmp_path / "ca.pem"
    cert = tmp_path / "client.pem"
    key = tmp_path / "client.key"
    ca.write_text("")
    cert.write_text("")
    key.write_text("")

    path = tmp_path / "kafka-access.yaml"
    path.write_text(
        f"""
kafka_access:
  profiles:
    - name: discovery
      scope: cluster
      bootstrap_servers: kafka.example:9093
      auth:
        type: bearer_token
        token: token-value
      capabilities:
        - list_topics
    - name: payments
      scope: topic
      bootstrap_servers: kafka.example:9093
      topics:
        - payments.*
      auth:
        type: mtls
        ca_cert: {ca}
        client_cert: {cert}
        client_key: {key}
      capabilities:
        - describe_topic
"""
    )

    access = load_kafka_access_config(str(path))
    cluster_profile = access.profile_for("list_topics")
    topic_profile = access.profile_for("describe_topic", topic="payments.events")

    assert access.valid
    assert cluster_profile.name == "discovery"
    assert topic_profile.name == "payments"
    assert (
        admin_config_from_profile(cluster_profile)["sasl.mechanisms"] == "OAUTHBEARER"
    )
    assert admin_config_from_profile(topic_profile)["security.protocol"] == "SSL"


def test_kafka_access_config_invalid_blocks_before_connect(monkeypatch, tmp_path):
    from beacon import kafka_runtime_connector

    path = tmp_path / "bad-access.yaml"
    path.write_text(
        """
kafka_access:
  profiles:
    - name: invalid
      scope: cluster
      auth:
        type: bearer_token
"""
    )

    def fail_if_called(config):
        raise AssertionError("AdminClient should not be constructed")

    monkeypatch.setattr(kafka_runtime_connector, "AdminClient", fail_if_called)

    findings = kafka_runtime_connector.analyze_kafka_cluster(
        bootstrap_server=None,
        access_config=str(path),
    )

    assert findings[0]["rule_id"] == "kafka.runtime.access.invalid"


def test_kafka_access_config_reports_auth_posture_findings(tmp_path):
    from beacon.diagnose.kafka.access_config import load_kafka_access_config

    path = tmp_path / "risky-access.yaml"
    path.write_text(
        """
kafka_access:
  profiles:
    - name: discovery
      scope: cluster
      bootstrap_servers: kafka.example:9092
      auth:
        type: plaintext
      capabilities:
        - list_topics
    - name: broad
      scope: all
      bootstrap_servers: kafka.example:9093
      auth:
        type: sasl_plain
        security_protocol: SASL_PLAINTEXT
        username: user
        password: pass
    - name: topic-unbounded
      scope: topic
      bootstrap_servers: kafka.example:9093
      auth:
        type: sasl_scram
        mechanism: SCRAM-SHA-256
        username: user
        password: pass
"""
    )

    access = load_kafka_access_config(str(path))
    rule_ids = {issue["rule_id"] for issue in access.posture_issues()}

    assert "kafka.runtime.access.auth.plaintext" in rule_ids
    assert "kafka.runtime.access.auth.sasl_without_ssl" in rule_ids
    assert "kafka.runtime.access.auth.sasl_plain" in rule_ids
    assert "kafka.runtime.access.scope.broad" in rule_ids
    assert "kafka.runtime.access.scope.topic_unbounded" in rule_ids
    assert "kafka.runtime.access.auth.scram_sha256" in rule_ids


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
    from beacon.engine import metadata_registry as rules_registry

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
    assert summary["score_status"] == "BLOCKED_BY_ANALYSIS_ERROR"
    assert summary["production_decision"] == "NOT READY"
    assert summary["survivability"] == "ANALYSIS BLOCKED"
    assert "Resolve analysis errors" in summary["recommended_action"]


def test_terraform_plan_json_is_scanned(tmp_path):
    import json

    from beacon.scanner import scan_file

    plan = {
        "format_version": "1.2",
        "resource_changes": [
            {
                "type": "aws_s3_bucket_public_access_block",
                "name": "bad_bucket_access",
                "change": {
                    "after": {
                        "block_public_acls": False,
                        "block_public_policy": True,
                        "ignore_public_acls": True,
                        "restrict_public_buckets": False,
                    }
                },
            }
        ],
    }
    plan_path = tmp_path / "tfplan.json"
    plan_path.write_text(json.dumps(plan))

    findings = scan_file(str(plan_path))

    assert any(
        finding["rule_id"] == "object_storage.public_access.enabled"
        for finding in findings
    )


def test_terraform_state_json_is_scanned(tmp_path):
    import json

    from beacon.scanner import scan_file

    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_s3_bucket",
                        "name": "data",
                        "values": {"bucket": "data"},
                    }
                ]
            }
        }
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state))

    findings = scan_file(str(state_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "object_storage.encryption.missing" in rule_ids
    assert "object_storage.versioning.missing" in rule_ids


def test_helm_chart_rendering_is_scanned(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from beacon import scanner

    chart_dir = tmp_path / "payments"
    templates_dir = chart_dir / "templates"
    templates_dir.mkdir(parents=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: payments\nversion: 0.1.0\n"
    )
    (templates_dir / "deployment.yaml").write_text("{{ .Values.placeholder }}\n")

    rendered_manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: api
          image: payments:latest
"""

    monkeypatch.setattr(scanner.shutil, "which", lambda binary: "/usr/bin/helm")
    monkeypatch.setattr(
        scanner.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=rendered_manifest),
    )

    findings = scanner.scan_path(str(chart_dir))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "k8s.workload.replicas.single" in rule_ids
    assert "k8s.workload.resources.missing" in rule_ids
    assert "k8s.image.latest_tag" in rule_ids


def test_helm_chart_without_helm_blocks_analysis(monkeypatch, tmp_path):
    from beacon import scanner

    chart_dir = tmp_path / "payments"
    (chart_dir / "templates").mkdir(parents=True)
    (chart_dir / "Chart.yaml").write_text(
        "apiVersion: v2\nname: payments\nversion: 0.1.0\n"
    )

    monkeypatch.setattr(scanner.shutil, "which", lambda binary: None)

    findings = scanner.scan_path(str(chart_dir))

    assert any(finding["rule_id"] == "helm.render.unavailable" for finding in findings)


def test_github_actions_deployment_risk_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    workflow = """
name: Release
on:
  pull_request_target:
  push:
    branches: [main]
permissions: write-all
jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy production
"""
    workflow_path = tmp_path / "release.yaml"
    workflow_path.write_text(workflow)

    findings = scan_file(str(workflow_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "cicd.deployment.environment.missing" in rule_ids
    assert "cicd.github.pull_request_target.used" in rule_ids
    assert "cicd.github.permissions.write_all" in rule_ids


def test_kubernetes_runtime_snapshot_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    snapshot = """
kubernetes_runtime:
  nodes:
    - name: node-a
      ready: false
      memory_pressure: true
  pods:
    - name: payments-api-123
      namespace: payments
      phase: Running
      restart_count: 8
      waiting_reason: CrashLoopBackOff
    - name: worker-456
      namespace: payments
      phase: Pending
  deployments:
    - name: payments-api
      namespace: payments
      desired_replicas: 3
      available_replicas: 1
"""
    snapshot_path = tmp_path / "k8s-runtime.yaml"
    snapshot_path.write_text(snapshot)

    findings = scan_file(str(snapshot_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "k8s.runtime.node.not_ready" in rule_ids
    assert "k8s.runtime.node.pressure" in rule_ids
    assert "k8s.runtime.pod.crash_loop" in rule_ids
    assert "k8s.runtime.pod.pending" in rule_ids
    assert "k8s.runtime.deployment.unavailable" in rule_ids


def test_deeper_aws_terraform_risks_are_scanned(tmp_path):
    from beacon.scanner import scan_file

    terraform = """
resource "aws_security_group" "open" {
  ingress {
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "db" {
  publicly_accessible = true
  backup_retention_period = 0
}

resource "aws_instance" "api" {
  ami = "ami-123"
  instance_type = "t3.micro"
}
"""
    tf_path = tmp_path / "main.tf"
    tf_path.write_text(terraform)

    findings = scan_file(str(tf_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "cloud.network.security_group.open_ingress" in rule_ids
    assert "cloud.database.rds.publicly_accessible" in rule_ids
    assert "cloud.database.rds.backup_retention_missing" in rule_ids
    assert "cloud.compute.ec2.detailed_monitoring.disabled" in rule_ids


def test_live_kubernetes_connector_uses_read_only_kubectl(monkeypatch):
    import json
    from types import SimpleNamespace

    from beacon import kubernetes_runtime_connector

    payloads = {
        "nodes": {
            "items": [
                {
                    "metadata": {"name": "node-a"},
                    "status": {
                        "conditions": [
                            {"type": "Ready", "status": "False"},
                            {"type": "MemoryPressure", "status": "True"},
                        ]
                    },
                }
            ]
        },
        "pods": {
            "items": [
                {
                    "metadata": {"name": "api-123", "namespace": "payments"},
                    "status": {
                        "phase": "Running",
                        "containerStatuses": [
                            {
                                "restartCount": 6,
                                "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                            }
                        ],
                    },
                }
            ]
        },
        "deployments": {
            "items": [
                {
                    "metadata": {"name": "api", "namespace": "payments"},
                    "spec": {"replicas": 3},
                    "status": {"availableReplicas": 1},
                }
            ]
        },
    }

    def fake_run(command, **kwargs):
        command_text = " ".join(command)

        if "get nodes" in command_text:
            return SimpleNamespace(stdout=json.dumps(payloads["nodes"]))
        if "get pods" in command_text:
            return SimpleNamespace(stdout=json.dumps(payloads["pods"]))
        if "get deployments" in command_text:
            return SimpleNamespace(stdout=json.dumps(payloads["deployments"]))

        raise AssertionError(command)

    monkeypatch.setattr(
        kubernetes_runtime_connector.shutil, "which", lambda binary: "/usr/bin/kubectl"
    )
    monkeypatch.setattr(kubernetes_runtime_connector.subprocess, "run", fake_run)

    findings = kubernetes_runtime_connector.analyze_kubernetes_cluster(
        namespace="payments"
    )
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "k8s.runtime.read_only_mode" in rule_ids
    assert "k8s.runtime.collection.success" in rule_ids
    assert "k8s.runtime.node.not_ready" in rule_ids
    assert "k8s.runtime.pod.crash_loop" in rule_ids
    assert "k8s.runtime.deployment.unavailable" in rule_ids


def test_kafka_broker_config_is_scanned():
    from beacon.rules import evaluate_kafka_config

    findings = evaluate_kafka_config(
        {
            "brokers": [
                {
                    "id": 1,
                    "default_replication_factor": 1,
                    "offsets_topic_replication_factor": 1,
                    "transaction_state_log_replication_factor": 1,
                    "auto_create_topics_enable": True,
                    "broker_rack": None,
                    "security_protocol": "PLAINTEXT",
                    "listener_security_protocol_map": "PLAINTEXT:PLAINTEXT",
                    "authorizer_class_name": None,
                    "allow_everyone_if_no_acl_found": True,
                    "unclean_leader_election_enable": True,
                    "controlled_shutdown_enable": False,
                }
            ]
        },
        "kafka.yaml",
    )
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.broker.default_replication_factor.low" in rule_ids
    assert "kafka.broker.offsets_replication_factor.low" in rule_ids
    assert "kafka.broker.transaction_log_replication_factor.low" in rule_ids
    assert "kafka.broker.auto_create_topics.enabled" in rule_ids
    assert "kafka.broker.unclean_leader_election.enabled" in rule_ids
    assert "kafka.broker.rack_awareness.missing" in rule_ids
    assert "kafka.broker.security.plaintext_listener" in rule_ids
    assert "kafka.broker.security.authorizer_missing" in rule_ids
    assert "kafka.broker.security.allow_everyone_if_no_acl" in rule_ids
    assert "kafka.broker.controlled_shutdown.disabled" in rule_ids
    assert "kafka.broker.client_quotas.missing" in rule_ids


def test_kafka_topic_schema_and_ownership_risks_are_scanned():
    from beacon.rules import evaluate_kafka_config

    findings = evaluate_kafka_config(
        {
            "topics": [
                {
                    "name": "payments",
                    "replication_factor": 3,
                    "partitions": 12,
                    "retention_ms": 86400000,
                    "retention_bytes": 1073741824,
                    "cleanup_policy": "delete",
                    "min_insync_replicas": 2,
                    "replica_placements": [
                        {
                            "partition": 0,
                            "replicas": [1, 2, 3],
                            "replica_racks": ["az-a", "az-a", "az-a"],
                        }
                    ],
                    "schema_compatibility": "NONE",
                }
            ]
        },
        "kafka.yaml",
    )
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.topic.schema_compatibility.unsafe" in rule_ids
    assert "kafka.topic.owner.missing" in rule_ids
    assert "kafka.topic.replica_placement.single_failure_domain" in rule_ids


def test_kafka_compacted_topic_operational_risks_are_scanned():
    from beacon.rules import evaluate_kafka_config

    findings = evaluate_kafka_config(
        {
            "kafka": {
                "topics": [
                    {
                        "name": "customer-state",
                        "replication_factor": 3,
                        "partitions": 12,
                        "cleanup_policy": "compact,delete",
                        "delete_retention_ms": 3600000,
                        "min_cleanable_dirty_ratio": 0.75,
                        "key_cardinality_estimate": 2500000,
                    }
                ]
            }
        },
        "kafka-compaction.yaml",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.topic.compacted_without_retention_bytes" in rule_ids
    assert "kafka.topic.compaction.tombstone_retention.low" in rule_ids
    assert "kafka.topic.compaction.dirty_ratio.high" in rule_ids
    assert "kafka.topic.compaction.key_cardinality.high" in rule_ids


def test_kafka_producer_and_consumer_client_risks_are_scanned():
    from beacon.rules import evaluate_kafka_config

    findings = evaluate_kafka_config(
        {
            "kafka": {
                "producers": [
                    {
                        "name": "checkout-producer",
                        "topic": "payments",
                        "acks": 1,
                        "enable_idempotence": False,
                        "max_in_flight_requests_per_connection": 10,
                        "compression_type": "none",
                    },
                    {
                        "name": "ledger-producer",
                        "topic": "ledger-events",
                        "acks": "all",
                        "enable_idempotence": True,
                        "max_in_flight_requests_per_connection": 10,
                        "compression_type": "zstd",
                    },
                ],
                "consumers": [
                    {
                        "name": "payment-worker",
                        "topic": "payments",
                        "group_id": "payment-worker",
                        "partitions": 2,
                        "consumer_concurrency": 5,
                        "enable_auto_commit": True,
                        "auto_offset_reset": "latest",
                        "max_poll_interval_ms": 30000,
                        "session_timeout_ms": 10000,
                        "heartbeat_interval_ms": 5000,
                        "retry_max_attempts": 5,
                    }
                ],
            }
        },
        "kafka-clients.yaml",
    )

    rule_ids = {finding["rule_id"] for finding in findings}

    assert "kafka.producer.acks.unsafe" in rule_ids
    assert "kafka.producer.idempotence.disabled" in rule_ids
    assert "kafka.producer.max_in_flight.unsafe" in rule_ids
    assert "kafka.producer.compression.missing" in rule_ids
    assert "kafka.consumer.auto_commit.enabled" in rule_ids
    assert "kafka.consumer.auto_offset_reset.latest" in rule_ids
    assert "kafka.consumer.poll_interval.too_low" in rule_ids
    assert "kafka.consumer.heartbeat_session.mismatch" in rule_ids
    assert "kafka.consumer.concurrency.exceeds_partitions" in rule_ids
    assert "kafka.consumer.dlq.missing" in rule_ids


def test_cloud_inventory_snapshot_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    inventory = """
cloud_inventory:
  resources:
    - type: aws_db_instance
      name: customer-db
      config:
        publicly_accessible: true
        backup_retention_period: 0
"""
    path = tmp_path / "cloud.yaml"
    path.write_text(inventory)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "cloud.database.rds.publicly_accessible" in rule_ids
    assert "cloud.database.rds.backup_retention_missing" in rule_ids


def test_topology_blast_radius_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    topology = """
topology:
  services:
    - name: auth
      criticality: critical
      instances: 1
    - name: payments
      owner: team-payments
      depends_on: [auth]
    - name: orders
      owner: team-orders
      depends_on: [auth]
    - name: profile
      owner: team-profile
      depends_on: [auth]
"""
    path = tmp_path / "topology.yaml"
    path.write_text(topology)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "topology.service.blast_radius.high" in rule_ids
    assert "topology.service.critical_single_instance" in rule_ids
    assert "topology.service.owner.missing" in rule_ids


def test_flow_runtime_snapshot_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    flow = """
flow_runtime:
  name: checkout
  signals:
    kafka_consumer_lag_increasing: true
    kafka_broker_unhealthy: false
    db_latency_ms: 850
    recent_deployment: true
    api_error_rate_percent: 7
    api_timeout_rate_percent: 4
    consumer_retry_rate_percent: 9
  components:
    api:
      type: api
      signals:
        unhealthy: true
    database:
      type: database
      signals:
        unhealthy: true
"""
    path = tmp_path / "flow-runtime.yaml"
    path.write_text(flow)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "flow.runtime.downstream_db_bottleneck" in rule_ids
    assert "flow.runtime.deployment_correlated_degradation" in rule_ids
    assert "flow.runtime.cascading_latency" in rule_ids
    assert "flow.runtime.component_unhealthy" in rule_ids


def test_diagnose_flow_uses_runtime_snapshot(monkeypatch, tmp_path):
    from beacon import cli

    path = tmp_path / "flow-runtime.yaml"
    path.write_text(
        """
flow_runtime:
  name: checkout
  signals:
    kafka_consumer_lag_increasing: true
    kafka_broker_unhealthy: false
    db_latency_ms: 900
"""
    )
    captured = {}

    monkeypatch.setattr(cli, "load_policy", lambda: {})

    def capture_report(findings, **kwargs):
        captured["findings"] = findings
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli, "print_report", capture_report)

    cli.diagnose_flow(str(path), html=False, open_report=False, output="json")

    assert any(
        finding["rule_id"] == "flow.runtime.downstream_db_bottleneck"
        for finding in captured["findings"]
    )
    assert captured["kwargs"]["output"] == "json"


def test_api_database_and_storage_runtime_snapshot_is_scanned(tmp_path):
    from beacon.scanner import scan_file

    snapshot = """
api_runtime:
  services:
    - name: checkout-api
      latency_p95_ms: 1400
      error_rate_percent: 6
      timeout_rate_percent: 4
      retry_rate_percent: 14
      recent_deployment: true

database_runtime:
  databases:
    - name: orders-db
      engine: postgres
      latency_ms: 720
      connection_pool_utilization_percent: 92
      lock_waits_high: true
      replication_lag_seconds: 120
      storage_used_percent: 88

storage_runtime:
  resources:
    - name: orders-volume
      type: block_volume
      used_percent: 91
      growth_percent_7d: 26
      iops_saturation_percent: 89
      backup_age_hours: 36
"""
    path = tmp_path / "platform-runtime.yaml"
    path.write_text(snapshot)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "api.runtime.latency_p95.high" in rule_ids
    assert "api.runtime.error_rate.high" in rule_ids
    assert "api.runtime.timeout_rate.high" in rule_ids
    assert "api.runtime.retry_amplification" in rule_ids
    assert "api.runtime.deployment_correlated_degradation" in rule_ids
    assert "database.runtime.latency.high" in rule_ids
    assert "database.runtime.connection_pool.exhaustion" in rule_ids
    assert "database.runtime.replication_lag.high" in rule_ids
    assert "database.runtime.lock_contention.high" in rule_ids
    assert "database.runtime.storage_saturation" in rule_ids
    assert "storage.runtime.capacity.high" in rule_ids
    assert "storage.runtime.growth_rate.high" in rule_ids
    assert "storage.runtime.iops_saturation.high" in rule_ids
    assert "storage.runtime.backup_stale" in rule_ids


def test_diagnose_snapshot_uses_general_runtime_snapshot(monkeypatch, tmp_path):
    from beacon import cli

    path = tmp_path / "api-runtime.yaml"
    path.write_text(
        """
api_runtime:
  name: checkout-api
  latency_p95_ms: 1500
"""
    )
    captured = {}

    monkeypatch.setattr(cli, "load_policy", lambda: {})

    def capture_report(findings, **kwargs):
        captured["findings"] = findings
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli, "print_report", capture_report)

    cli.diagnose_snapshot(str(path), html=False, open_report=False, output="json")

    assert any(
        finding["rule_id"] == "api.runtime.latency_p95.high"
        for finding in captured["findings"]
    )
    assert captured["kwargs"]["output"] == "json"
