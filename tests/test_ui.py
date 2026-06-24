from io import BytesIO
from email.message import Message
import mimetypes
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import subprocess
import sys

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
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
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
    assert "Download Evidence JSON" in ui.HTML
    assert "downloadReleaseEvidence" in ui.HTML
    assert "beacon-release-evidence.json" in ui.HTML
    assert "Top Reasons" in ui.HTML
    assert "Root Cause Hypotheses" in ui.HTML
    assert 'id="environment"' in ui.HTML
    assert "Risk Points" in ui.HTML
    assert "Business Risk Categories" in ui.HTML
    assert "release-gate-card" in ui.HTML
    assert "Is this production ready?" in ui.HTML
    assert "Business risk" in ui.HTML
    assert 'id="intelligence_context"' in ui.HTML
    assert "Runtime Diagnosis" in ui.HTML
    assert "Incident Diagnosis" in ui.HTML
    assert "Primary likely cause" in ui.HTML
    assert "Why Beacon thinks this" in ui.HTML
    assert "Kafka consumer group diagnosis" in ui.HTML
    assert "Flow bottleneck ranking" in ui.HTML
    assert "Before / after deployment" in ui.HTML
    assert 'id="deployment_events"' in ui.HTML
    assert "Diagnostic Timeline" in ui.HTML
    assert 'id="kafka_incident_scenario"' in ui.HTML
    assert "Rebalance storm" in ui.HTML


def test_ui_e2e_static_config_upload_returns_backend_findings():
    payload = run_multipart_ui_check(
        fields={"mode": "direct", "environment": "prod"},
        files={"static_config": "examples/bad-infra/kafka-topics.yaml"},
    )

    rule_ids = {finding["rule_id"] for finding in payload["findings"]}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert payload["readiness_summary"]["environment"] == "prod"
    assert payload["readiness_summary"]["production_decision"] == "NOT READY"
    assert payload["readiness_summary"]["release_gate"]["answer"] == "No"
    assert payload["readiness_summary"]["release_gate"]["why_not"]
    assert payload["readiness_summary"]["release_gate"]["fix_first"]


def test_ui_http_smoke_script_passes():
    result = subprocess.run(
        [sys.executable, "scripts/ui_smoke_check.py"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "ui smoke ok" in result.stdout


def test_ui_returns_findings_in_severity_order(monkeypatch):
    def fake_scan_path(_path):
        return [
            {
                "rule_id": "low.rule",
                "domain": "kafka",
                "category": "operational_safety",
                "severity": "LOW",
                "title": "Low finding",
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
                "title": "Critical finding",
                "impact": "impact",
                "recommendation": "recommendation",
                "file": "x",
                "evidence": {},
                "tags": [],
            },
        ]

    monkeypatch.setattr(ui, "scan_path", fake_scan_path)

    payload = ui.run_beacon_check({"environment": "prod"}, {"static_config": "ignored"})

    assert [finding["severity"] for finding in payload["findings"]] == [
        "CRITICAL",
        "LOW",
    ]


def test_ui_e2e_runtime_snapshot_upload_returns_root_cause_findings():
    payload = run_multipart_ui_check(
        fields={"mode": "direct"},
        files={"runtime_snapshot": "examples/supported/runtime/all-runtime.yaml"},
    )

    rule_ids = {finding["rule_id"] for finding in payload["findings"]}

    assert "flow.runtime.cascading_latency" in rule_ids
    assert "database.runtime.connection_pool.exhaustion" in rule_ids
    assert payload["readiness_summary"]["root_cause_hypotheses"]
    assert payload["diagnostic_summary"]["diagnostic_status"] == ("ROOT_CAUSE_CANDIDATES_FOUND")
    assert payload["diagnostic_summary"]["flow_bottleneck_rankings"]


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


def test_kafka_ui_passes_multiple_bootstrap_servers(monkeypatch):
    from beacon import ui

    calls = []

    def fake_analyze_kafka_cluster(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)

    ui.run_kafka_check(
        {
            "mode": "direct",
            "bootstrap_server": "broker-1:9092\nbroker-2:9092, broker-3:9092",
            "security_protocol": "SSL",
            "max_topics": "50",
            "max_groups": "20",
        },
        {},
    )

    assert calls[0]["bootstrap_server"] == ("broker-1:9092\nbroker-2:9092, broker-3:9092")


def test_kafka_ui_incident_scenario_returns_incident_diagnosis():
    from beacon import ui

    result = ui.run_beacon_check(
        {"mode": "direct", "kafka_incident_scenario": "quota_throttling"},
        {},
    )

    rule_ids = {finding["rule_id"] for finding in result["findings"]}

    assert "kafka.runtime.producer_throttle.high" in rule_ids
    assert "kafka.runtime.fetch_throttle.high" in rule_ids
    assert (
        result["diagnostic_summary"]["incident_diagnosis"]["title"]
        == "Are clients failing because of auth, ACLs, quotas, or throttling?"
    )
    assert (
        result["diagnostic_summary"]["incident_diagnosis"]["runbook"]["title"]
        == "Kafka Auth / Quota / Throttling Runbook"
    )
    assert (
        result["diagnostic_summary"]["incident_diagnosis"]["evidence_quality"]["status"]
        == "ACTIONABLE"
    )
    assert "Kafka incident demo: Quota / throttling pressure" in result["request_scope"]["inputs"]


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
    monkeypatch.setattr(ui, "analyze_schema_registry_config", fake_analyze_schema_registry_config)

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

    topics = parse_expected_topic_subjects("payments: payments-key, payments-value\norders\n")

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
        lambda path: calls.append(("static", path)) or [finding("static.rule", "infra")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_runtime_snapshot_file",
        lambda path: calls.append(("snapshot", path)) or [finding("snapshot.rule", "runtime")],
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
        lambda path: calls.append(("acls", path)) or [finding("kafka.acl.rule", "kafka")],
    )
    monkeypatch.setattr(
        ui,
        "analyze_kafka_history_file",
        lambda path: calls.append(("history", path)) or [finding("kafka.history.rule", "kafka")],
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


def test_beacon_ui_exposes_kafka_scope_and_filters(monkeypatch):
    from beacon import ui

    calls = []

    def fake_analyze_kafka_cluster(**kwargs):
        calls.append(kwargs)
        return [
            {
                "rule_id": "kafka.consumer_group.lag.high",
                "domain": "kafka",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "Kafka consumer lag high",
                "impact": "Consumers are behind.",
                "recommendation": "Inspect the group.",
                "file": "runtime-kafka",
                "evidence": {
                    "consumer_group": "checkout-consumer",
                    "topic": "payments",
                    "total_lag": 10000,
                },
                "tags": [],
            }
        ]

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)

    result = ui.run_beacon_check(
        {
            "mode": "direct",
            "bootstrap_server": "localhost:9092",
            "topic": "payments",
            "consumer_group": "checkout-consumer",
            "max_topics": "5",
            "max_groups": "1",
        },
        {},
    )

    assert calls[0]["topic"] == "payments"
    assert calls[0]["consumer_group"] == "checkout-consumer"
    assert calls[0]["max_topics"] == 5
    assert calls[0]["max_groups"] == 1
    assert result["request_scope"]["kafka_topic"] == "payments"
    assert result["request_scope"]["kafka_consumer_group"] == "checkout-consumer"
    assert "Kafka live" in result["request_scope"]["inputs"]
    assert result["diagnostic_summary"]["scope"]["kafka_consumer_group_scope"] is None
    assert (
        result["diagnostic_summary"]["consumer_group_diagnoses"][0]["consumer_group"]
        == "checkout-consumer"
    )
    assert (
        result["diagnostic_summary"]["consumer_group_diagnoses"][0]["evidence_quality"]["status"]
        == "NEEDS_MORE_EVIDENCE"
    )


def test_beacon_ui_exposes_scoped_consumer_group_banner(monkeypatch):
    from beacon import ui

    def fake_analyze_kafka_cluster(**kwargs):
        return [
            {
                "rule_id": "kafka.runtime.connection.success",
                "domain": "kafka",
                "category": "runtime_stability",
                "severity": "LOW",
                "title": "Kafka cluster connection successful",
                "impact": "Connected.",
                "recommendation": "No action required.",
                "file": "runtime-kafka",
                "evidence": {
                    "consumer_group_filter": "checkout-consumer",
                    "topic_scope": "consumer_group_committed_topics",
                    "analyzed_topic_count": 2,
                    "cluster_topic_count": 40,
                },
                "tags": [],
            },
            {
                "rule_id": "kafka.consumer_group.lag.high",
                "domain": "kafka",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "Kafka consumer lag high",
                "impact": "Consumers are behind.",
                "recommendation": "Inspect the group.",
                "file": "runtime-kafka",
                "evidence": {
                    "consumer_group": "checkout-consumer",
                    "topic": "payments",
                    "total_lag": 10000,
                },
                "tags": [],
            },
        ]

    monkeypatch.setattr(ui, "analyze_kafka_cluster", fake_analyze_kafka_cluster)

    result = ui.run_beacon_check(
        {
            "mode": "direct",
            "bootstrap_server": "localhost:9092",
            "consumer_group": "checkout-consumer",
        },
        {},
    )

    scope = result["diagnostic_summary"]["scope"]["kafka_consumer_group_scope"]
    assert scope["consumer_group"] == "checkout-consumer"
    assert scope["status"] == "SCOPED_TO_COMMITTED_TOPICS"
    assert scope["analyzed_topic_count"] == 2


def test_beacon_ui_correlates_deployment_events_after_runtime_inputs(monkeypatch):
    from beacon import ui

    seen_existing = []

    monkeypatch.setattr(
        ui,
        "analyze_runtime_snapshot_file",
        lambda path: [
            {
                "rule_id": "api.runtime.deployment_correlated_degradation",
                "domain": "api",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "API degraded after deployment",
                "impact": "API degraded after rollout.",
                "recommendation": "Inspect deployment.",
                "file": path,
                "evidence": {"service": "checkout-api"},
                "tags": [],
            }
        ],
    )

    def fake_deployment_events(path, existing_findings=None):
        seen_existing.extend(item["rule_id"] for item in existing_findings)
        return [
            {
                "rule_id": "deployment.runtime.degradation_correlated",
                "domain": "deployment",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "Runtime degradation is correlated with deployment events",
                "impact": "Deployment events align with degradation.",
                "recommendation": "Review rollout.",
                "file": path,
                "evidence": {
                    "latest_deployment": {
                        "service": "checkout-api",
                        "deployed_at": "2026-06-03T10:20:00Z",
                    },
                    "deployment_count": 1,
                    "matched_rule_ids": ["api.runtime.deployment_correlated_degradation"],
                },
                "tags": [],
            }
        ]

    monkeypatch.setattr(ui, "analyze_deployment_events_file", fake_deployment_events)

    result = ui.run_beacon_check(
        {"mode": "direct"},
        {
            "runtime_snapshot": "/tmp/runtime.yaml",
            "deployment_events": "/tmp/deployments.yaml",
        },
    )

    assert "api.runtime.deployment_correlated_degradation" in seen_existing
    assert "Deployment events" in result["request_scope"]["inputs"]
    assert result["diagnostic_timeline"]
    assert any(
        item["rule_id"] == "deployment.runtime.degradation_correlated"
        for item in result["diagnostic_timeline"]
    )
    assert (
        result["diagnostic_summary"]["primary_hypothesis"]["correlation_id"]
        == "correlation.root_cause.deployment_regression"
    )


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
    monkeypatch.setattr(ui, "analyze_kafka_cluster", lambda **kwargs: calls.append(kwargs) or [])

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
    monkeypatch.setattr(ui, "analyze_kafka_cluster", lambda **kwargs: calls.append(kwargs) or [])

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


def test_ui_build_server_falls_back_to_next_available_port(monkeypatch):
    from beacon import ui

    bound_ports = []

    class FakeServer:
        def __init__(self, address, handler):
            host, port = address
            if port == 8765:
                raise OSError(48, "Address already in use")
            bound_ports.append(port)
            self.server_address = (host, port)

    monkeypatch.setattr(ui, "ThreadingHTTPServer", FakeServer)

    server, port = ui.build_server("127.0.0.1", 8765)

    assert port == 8766
    assert server.server_address == ("127.0.0.1", 8766)
    assert bound_ports == [8766]


def test_ui_build_server_can_fail_fast_when_requested(monkeypatch):
    from beacon import ui

    class FakeServer:
        def __init__(self, address, handler):
            raise OSError(48, "Address already in use")

    monkeypatch.setattr(ui, "ThreadingHTTPServer", FakeServer)

    try:
        ui.build_server("127.0.0.1", 8765, allow_port_fallback=False)
    except OSError as error:
        assert error.errno == 48
    else:
        raise AssertionError("Expected OSError when port fallback is disabled")
