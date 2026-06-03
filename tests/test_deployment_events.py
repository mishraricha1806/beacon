from beacon.deployment_events import analyze_deployment_events_file


def finding(rule_id, severity="HIGH"):
    return {
        "rule_id": rule_id,
        "domain": "kafka",
        "category": "runtime_stability",
        "severity": severity,
        "title": rule_id,
        "impact": "Runtime degradation detected.",
        "recommendation": "Investigate the signal.",
        "file": "runtime.yaml",
        "evidence": {"consumer_group": "checkout-consumer"},
        "tags": [],
    }


def test_deployment_events_load_and_correlate_with_runtime_findings(tmp_path):
    path = tmp_path / "deployment-events.yaml"
    path.write_text(
        """
deployment_events:
  - service: checkout-consumer
    environment: staging
    version: v1.42.0
    deployed_at: "2026-06-03T10:15:00Z"
    commit: abc123
    namespace: payments
    changed_components:
      - consumer
      - database-client
"""
    )

    findings = analyze_deployment_events_file(
        path,
        existing_findings=[finding("kafka.consumer_group.lag.high")],
    )

    rule_ids = {item["rule_id"] for item in findings}
    correlated = next(
        item
        for item in findings
        if item["rule_id"] == "deployment.runtime.degradation_correlated"
    )

    assert "deployment.events.loaded" in rule_ids
    assert "deployment.runtime.degradation_correlated" in rule_ids
    assert correlated["severity"] == "HIGH"
    assert correlated["evidence"]["deployment_count"] == 1
    assert correlated["evidence"]["latest_deployment"]["service"] == "checkout-consumer"
    assert correlated["evidence"]["matched_rule_ids"] == [
        "kafka.consumer_group.lag.high"
    ]


def test_deployment_events_empty_input_is_low_signal(tmp_path):
    path = tmp_path / "deployment-events.yaml"
    path.write_text("deployment_events: []\n")

    findings = analyze_deployment_events_file(path)

    assert findings[0]["rule_id"] == "deployment.events.empty"
    assert findings[0]["severity"] == "LOW"
    assert findings[0]["evidence"]["event_count"] == 0
