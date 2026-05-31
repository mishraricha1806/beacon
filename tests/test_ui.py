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


def test_kafka_ui_combines_schema_registry_findings(monkeypatch):
    from beacon import ui

    calls = []

    def fake_analyze_kafka_cluster(**kwargs):
        return []

    def fake_analyze_schema_registry_config(path, timeout=5):
        calls.append((path, timeout))
        return [
            {
                "rule_id": "schema_registry.runtime.read_only_mode",
                "domain": "kafka",
                "category": "operational_safety",
                "severity": "INFO",
                "title": "Schema Registry read-only mode",
                "impact": "No mutation will be performed.",
                "recommendation": "No action required.",
                "file": path,
                "evidence": {},
                "tags": [],
            }
        ]

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)
    monkeypatch.setattr(
        ui, "analyze_schema_registry_config", fake_analyze_schema_registry_config
    )

    result = ui.run_kafka_check(
        {
            "mode": "direct",
            "bootstrap_server": "localhost:9092",
            "security_protocol": "PLAINTEXT",
            "max_topics": "50",
            "max_groups": "20",
            "schema_registry_url": "http://schema-registry.local:8081",
            "schema_registry_auth_type": "bearer_token",
            "schema_registry_token": "token",
            "schema_registry_max_subjects": "10",
            "schema_registry_expected_topics": "payments: payments-key, payments-value",
        },
        {
            "schema_registry_ca_cert": "/tmp/ca.pem",
            "schema_registry_client_cert": "/tmp/client.pem",
            "schema_registry_client_key": "/tmp/client.key",
        },
    )

    assert calls[0][1] == 5
    assert result["findings"][0]["rule_id"] == "schema_registry.runtime.read_only_mode"


def test_kafka_ui_builds_schema_registry_tls_from_uploaded_certs():
    from beacon.ui import build_schema_registry_tls

    tls = build_schema_registry_tls(
        {
            "schema_registry_ca_cert": "/tmp/ca.pem",
            "schema_registry_client_cert": "/tmp/client.pem",
            "schema_registry_client_key": "/tmp/client.key",
        }
    )

    assert tls == {
        "ca_cert": "/tmp/ca.pem",
        "client_cert": "/tmp/client.pem",
        "client_key": "/tmp/client.key",
    }


def test_kafka_ui_uses_uploaded_schema_registry_config(monkeypatch):
    from beacon import ui

    calls = []

    monkeypatch.setattr(ui, "analyze_kafka_cluster", lambda **kwargs: [])
    monkeypatch.setattr(
        ui,
        "analyze_schema_registry_config",
        lambda path, timeout=5: calls.append((path, timeout)) or [],
    )

    ui.run_kafka_check(
        {
            "mode": "direct",
            "max_topics": "5",
            "max_groups": "0",
            "schema_registry_timeout": "2",
        },
        {"schema_registry_config": "/tmp/schema-registry.yaml"},
    )

    assert calls == [("/tmp/schema-registry.yaml", 2)]


def test_kafka_ui_parses_expected_topic_subjects():
    from beacon.ui import parse_expected_topic_subjects

    topics = parse_expected_topic_subjects(
        "payments: payments-key, payments-value\norders\n"
    )

    assert topics == [
        {"name": "payments", "subjects": ["payments-key", "payments-value"]},
        {"name": "orders"},
    ]
