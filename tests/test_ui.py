def test_kafka_ui_run_check_uses_existing_report_contract(monkeypatch):
    from beacon import ui

    def fake_analyze_kafka_cluster(**kwargs):
        assert kwargs["bootstrap_server"] == "localhost:9092"
        assert kwargs["security_protocol"] == "PLAINTEXT"
        return [
            {
                "rule_id": "kafka.runtime.read_only_mode",
                "domain": "kafka",
                "category": "runtime_stability",
                "severity": "INFO",
                "title": "Read-only mode",
                "impact": "No mutation will be performed.",
                "recommendation": "No action required.",
                "file": "runtime-kafka",
                "evidence": {},
                "tags": [],
            }
        ]

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)

    result = ui.run_kafka_check(
        {
            "mode": "direct",
            "bootstrap_server": "localhost:9092",
            "security_protocol": "PLAINTEXT",
            "max_topics": "50",
            "max_groups": "20",
        },
        {},
    )

    assert result["score"] == 100
    assert result["score_status"] == "CALCULATED"
    assert result["findings"][0]["rule_id"] == "kafka.runtime.read_only_mode"


def test_kafka_ui_access_mode_uses_uploaded_access_config(monkeypatch):
    from beacon import ui

    calls = []

    def fake_analyze_kafka_cluster(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)

    ui.run_kafka_check(
        {
            "mode": "access",
            "max_topics": "5",
            "max_groups": "0",
        },
        {"access_config": "/tmp/access.yaml"},
    )

    assert calls[0]["access_config"] == "/tmp/access.yaml"
    assert calls[0]["max_topics"] == 5
    assert calls[0]["max_groups"] == 0
