from beacon.correlations.root_cause import correlate_findings


def finding(rule_id, domain, severity="HIGH", title=None, evidence=None):
    return {
        "rule_id": rule_id,
        "domain": domain,
        "category": "runtime_stability",
        "severity": severity,
        "title": title or rule_id,
        "impact": "",
        "recommendation": "",
        "file": "runtime.yaml",
        "evidence": evidence or {},
        "tags": [],
    }


def test_correlates_downstream_database_bottleneck_first():
    hypotheses = correlate_findings(
        [
            finding("flow.runtime.downstream_db_bottleneck", "flow"),
            finding("database.runtime.latency.high", "database"),
            finding(
                "database.runtime.connection_pool.exhaustion", "database", "CRITICAL"
            ),
            finding("api.runtime.latency_p95.high", "api"),
        ]
    )

    assert hypotheses
    assert (
        hypotheses[0]["correlation_id"]
        == "correlation.root_cause.downstream_database_bottleneck"
    )
    assert hypotheses[0]["confidence"] == "HIGH"
    assert (
        "database.runtime.connection_pool.exhaustion"
        in hypotheses[0]["matched_rule_ids"]
    )


def test_readiness_summary_includes_root_cause_hypotheses():
    from beacon.readiness.kafka.readiness_engine import calculate_readiness

    summary = calculate_readiness(
        [
            finding("flow.runtime.cascading_latency", "flow", "CRITICAL"),
            finding("api.runtime.retry_amplification", "api", "CRITICAL"),
            finding("api.runtime.timeout_rate.high", "api"),
        ]
    )

    assert summary["root_cause_hypotheses"]
    assert (
        summary["root_cause_hypotheses"][0]["correlation_id"]
        == "correlation.root_cause.retry_cascade"
    )


def test_kafka_only_consumer_side_does_not_infer_database_bottleneck():
    hypotheses = correlate_findings(
        [
            finding("kafka.consumer_group.decision.consumer_side", "kafka"),
            finding("kafka.consumer_group.lag.high", "kafka"),
        ]
    )

    correlation_ids = {hypothesis["correlation_id"] for hypothesis in hypotheses}

    assert (
        "correlation.root_cause.downstream_database_bottleneck" not in correlation_ids
    )
    assert "correlation.root_cause.kafka_consumer_observation" in correlation_ids


def test_kafka_single_broker_gets_kafka_native_hypothesis():
    hypotheses = correlate_findings(
        [
            finding("kafka.cluster.broker_count.low", "kafka"),
            finding("kafka.topic.replication_factor.low", "kafka", "CRITICAL"),
            finding("kafka.cluster.under_min_isr_partitions", "kafka", "CRITICAL"),
        ]
    )

    assert hypotheses
    assert (
        hypotheses[0]["correlation_id"]
        == "correlation.root_cause.kafka_single_broker_topology"
    )


def test_kafka_schema_and_payload_risks_are_kafka_native():
    hypotheses = correlate_findings(
        [
            finding("schema_registry.compatibility.global_unsafe", "kafka", "HIGH"),
            finding("kafka.topic.max_message_bytes.large", "kafka", "HIGH"),
            finding("kafka.topic.retention_ms.unbounded", "kafka", "HIGH"),
        ]
    )

    correlation_ids = [hypothesis["correlation_id"] for hypothesis in hypotheses]

    assert "correlation.root_cause.kafka_schema_governance" in correlation_ids
    assert "correlation.root_cause.kafka_payload_storage_growth" in correlation_ids
