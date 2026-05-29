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
            finding("database.runtime.connection_pool.exhaustion", "database", "CRITICAL"),
            finding("api.runtime.latency_p95.high", "api"),
        ]
    )

    assert hypotheses
    assert (
        hypotheses[0]["correlation_id"]
        == "correlation.root_cause.downstream_database_bottleneck"
    )
    assert hypotheses[0]["confidence"] == "HIGH"
    assert "database.runtime.connection_pool.exhaustion" in hypotheses[0]["matched_rule_ids"]


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
