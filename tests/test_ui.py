from io import BytesIO
from email.message import Message
import mimetypes
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from beacon import ui


def build_multipart(fields=None, files=None):
    boundary = f"----beacon-test-{uuid4().hex}"
    body = bytearray()

    for name, value in (fields or {}).items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(str(value).encode())
        body.extend(b"\r\n")

    for name, file_path in (files or {}).items():
        file_path = Path(file_path)
        content_type = (
            mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        )
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{file_path.name}"\r\n'
            ).encode()
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    return (
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        bytes(body),
    )


def run_multipart_ui_check(fields=None, files=None):
    headers, body = build_multipart(fields=fields, files=files)
    message = Message()
    message["Content-Type"] = headers["Content-Type"]
    message["Content-Length"] = str(len(body))
    handler = SimpleNamespace(headers=message, rfile=BytesIO(body))
    parsed_fields, parsed_files = ui.parse_multipart(handler)
    return ui.run_beacon_check(parsed_fields, parsed_files)


def test_ui_e2e_homepage_template_contains_run_surface():
    assert "Beacon Readiness Console" in ui.HTML
    assert "Run Beacon Readiness" in ui.HTML
    assert "/api/beacon" in ui.HTML
    assert 'id="beacon-form"' in ui.HTML
    assert 'value="static"' in ui.HTML
    assert 'value="runtime"' in ui.HTML
    assert 'value="flow"' in ui.HTML
    assert "Download JSON" in ui.HTML
    assert "Top Reasons" in ui.HTML
    assert "Root Cause Hypotheses" in ui.HTML
    assert 'id="environment"' in ui.HTML
    assert "Risk Points" in ui.HTML
    assert "Business Risk Categories" in ui.HTML


def test_ui_e2e_static_config_upload_returns_backend_findings():
    payload = run_multipart_ui_check(
        fields={"mode": "direct", "environment": "prod"},
        files={"static_config": "examples/bad-infra/kafka-topics.yaml"},
    )

    rule_ids = {finding["rule_id"] for finding in payload["findings"]}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert payload["readiness_summary"]["environment"] == "prod"
    assert payload["readiness_summary"]["production_decision"] == "NOT READY"


def test_ui_e2e_runtime_snapshot_upload_returns_root_cause_findings():
    payload = run_multipart_ui_check(
        fields={"mode": "direct"},
        files={"runtime_snapshot": "examples/supported/runtime/all-runtime.yaml"},
    )

    rule_ids = {finding["rule_id"] for finding in payload["findings"]}

    assert "flow.runtime.cascading_latency" in rule_ids
    assert "database.runtime.connection_pool.exhaustion" in rule_ids
    assert payload["readiness_summary"]["root_cause_hypotheses"]


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
            "churn_samples": "3",
            "churn_interval_seconds": "0.5",
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


def test_beacon_ui_combines_generic_domain_inputs(monkeypatch):
    from beacon import ui

    calls = []

    def finding(rule_id, domain):
        return {
            "rule_id": rule_id,
            "domain": domain,
            "category": "runtime_stability",
            "severity": "INFO",
            "title": rule_id,
            "impact": "impact",
            "recommendation": "recommendation",
            "file": domain,
            "evidence": {},
            "tags": [],
        }

    monkeypatch.setattr(
        ui,
        "scan_path",
        lambda path: calls.append(("static", path))
        or [finding("static.rule", "infra")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_runtime_snapshot_file",
        lambda path: calls.append(("snapshot", path))
        or [finding("snapshot.rule", "runtime")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_flow_file",
        lambda path: calls.append(("flow", path)) or [finding("flow.rule", "flow")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_prometheus_config",
        lambda path, timeout=5: calls.append(("prometheus", path, timeout))
        or [finding("prometheus.rule", "prometheus")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_opentelemetry_file",
        lambda path: calls.append(("opentelemetry", path))
        or [finding("opentelemetry.rule", "opentelemetry")],
    )
    monkeypatch.setattr(ui, "analyze_kafka_cluster", lambda **kwargs: [])
    monkeypatch.setattr(
        ui,
        "analyze_kafka_acl_file",
        lambda path: calls.append(("acls", path))
        or [finding("kafka.acl.rule", "kafka")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_kafka_history_file",
        lambda path: calls.append(("history", path))
        or [finding("kafka.history.rule", "kafka")],
    )

    result = ui.run_beacon_check(
        {"mode": "direct", "prometheus_timeout": "2"},
        {
            "static_config": "/tmp/static.yaml",
            "runtime_snapshot": "/tmp/runtime.yaml",
            "flow_snapshot": "/tmp/flow.yaml",
            "prometheus_config": "/tmp/prometheus.yaml",
            "opentelemetry_file": "/tmp/otel.yaml",
            "kafka_acl_export": "/tmp/acls.yaml",
            "kafka_history": "/tmp/history.yaml",
        },
    )

    assert {finding["rule_id"] for finding in result["findings"]} == {
        "static.rule",
        "snapshot.rule",
        "flow.rule",
        "prometheus.rule",
        "opentelemetry.rule",
        "kafka.acl.rule",
        "kafka.history.rule",
    }
    assert ("prometheus", "/tmp/prometheus.yaml", 2) in calls
    assert ("acls", "/tmp/acls.yaml") in calls
    assert ("history", "/tmp/history.yaml") in calls


def test_beacon_ui_passes_collector_timeouts(monkeypatch):
    from beacon import ui

    calls = []
    monkeypatch.setattr(
        ui,
        "analyze_prometheus_config",
        lambda path, timeout=5: calls.append(("prometheus", path, timeout)) or [],
    )
    monkeypatch.setattr(
        ui,
        "analyze_schema_registry_config",
        lambda path, timeout=5: calls.append(("schema", path, timeout)) or [],
    )

    ui.run_beacon_check(
        {
            "mode": "direct",
            "prometheus_timeout": "7",
            "schema_registry_timeout": "9",
        },
        {
            "prometheus_config": "/tmp/prometheus.yaml",
            "schema_registry_config": "/tmp/schema-registry.yaml",
        },
    )

    assert ("prometheus", "/tmp/prometheus.yaml", 7) in calls
    assert ("schema", "/tmp/schema-registry.yaml", 9) in calls


def test_beacon_ui_does_not_run_kafka_without_kafka_inputs(monkeypatch):
    from beacon import ui

    calls = []
    monkeypatch.setattr(
        ui, "analyze_kafka_cluster", lambda **kwargs: calls.append(kwargs) or []
    )

    result = ui.run_beacon_check({"mode": "direct"}, {})

    assert calls == []
    assert result["score"] == 100


def test_beacon_ui_runs_live_kubernetes_when_enabled(monkeypatch):
    from beacon import ui

    calls = []
    monkeypatch.setattr(
        ui,
        "analyze_kubernetes_cluster",
        lambda **kwargs: calls.append(kwargs) or [],
    )

    ui.run_beacon_check(
        {
            "mode": "direct",
            "kubernetes_live": "true",
            "kubernetes_namespace": "payments",
            "kubernetes_context": "prod",
        },
        {"kubernetes_kubeconfig": "/tmp/kubeconfig"},
    )

    assert calls == [
        {
            "namespace": "payments",
            "context": "prod",
            "kubeconfig": "/tmp/kubeconfig",
        }
    ]


def test_beacon_ui_passes_kafka_churn_sampling_options(monkeypatch):
    from beacon import ui

    calls = []
    monkeypatch.setattr(
        ui, "analyze_kafka_cluster", lambda **kwargs: calls.append(kwargs) or []
    )

    ui.run_beacon_check(
        {
            "mode": "direct",
            "bootstrap_server": "localhost:9092",
            "churn_samples": "4",
            "churn_interval_seconds": "0.25",
        },
        {},
    )

    assert calls[0]["churn_samples"] == 4
    assert calls[0]["churn_interval_seconds"] == 0.25
