from beacon.diagnose.diagnostic_engine import build_diagnostic_summary


def finding(rule_id, evidence=None, severity="HIGH"):
    return {
        "rule_id": rule_id,
        "domain": "flow",
        "category": "runtime_stability",
        "severity": severity,
        "title": rule_id,
        "impact": "impact",
        "recommendation": "recommendation",
        "file": "flow.yaml",
        "evidence": evidence or {},
        "tags": [],
    }


def test_flow_bottleneck_ranking_identifies_database_first():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "checkout",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 900,
                },
            ),
            finding(
                "flow.runtime.component_unhealthy",
                {
                    "flow": "checkout",
                    "component": "consumer",
                    "component_type": "consumer",
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "checkout"
    assert ranking["top_bottleneck"] == "database"
    assert ranking["top_confidence"] == "HIGH"
    assert ranking["components"][0]["component"] == "database"
    assert ranking["components"][0]["status"] == "likely_bottleneck"


def test_flow_bottleneck_ranking_identifies_retry_cascade_path():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.cascading_latency",
                {
                    "flow": "checkout",
                    "api_timeout_rate_percent": 5,
                    "consumer_retry_rate_percent": 12,
                    "kafka_consumer_lag_increasing": True,
                },
                severity="CRITICAL",
            )
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]
    components = [component["component"] for component in ranking["components"]]

    assert ranking["top_bottleneck"] == "api"
    assert components[:3] == ["api", "consumer", "kafka"]
