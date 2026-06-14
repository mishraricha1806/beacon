import json


class FakeSchemaRegistryResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_schema_registry_live_metadata_maps_to_kafka_readiness_findings(monkeypatch, tmp_path):
    from beacon import schema_registry_connector

    config = """
schema_registry:
  url: http://schema-registry.local:8081
  max_subjects: 2
  expected_topics:
    - name: payments
    - name: audit-events
      subjects:
        - audit-events-value
"""
    path = tmp_path / "schema-registry.yaml"
    path.write_text(config)

    payloads = {
        "/subjects": ["payments-key", "payments-value"],
        "/config": {"compatibilityLevel": "NONE"},
        "/config/payments-key": {"compatibilityLevel": "BACKWARD"},
        "/config/payments-value": {"compatibilityLevel": "DISABLED"},
        "/subjects/payments-key/versions/latest": {
            "subject": "payments-key",
            "version": 3,
            "schema": "{}",
            "schemaType": "AVRO",
        },
        "/subjects/payments-value/versions/latest": {
            "subject": "payments-value",
            "version": 4,
            "schema": "{}",
        },
    }

    def fake_urlopen(request, timeout=None):
        suffix = request.full_url.replace("http://schema-registry.local:8081", "")
        return FakeSchemaRegistryResponse(payloads[suffix])

    monkeypatch.setattr(schema_registry_connector.urllib.request, "urlopen", fake_urlopen)

    findings = schema_registry_connector.analyze_schema_registry_config(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "schema_registry.runtime.read_only_mode" in rule_ids
    assert "schema_registry.compatibility.global_unsafe" in rule_ids
    assert "schema_registry.subject.compatibility.unsafe" in rule_ids
    assert "schema_registry.topic.subject.missing" in rule_ids
    assert "schema_registry.subject.schema_type.missing" in rule_ids


def test_schema_registry_missing_url_blocks_analysis(tmp_path):
    from beacon.schema_registry_connector import analyze_schema_registry_config

    path = tmp_path / "schema-registry.yaml"
    path.write_text("schema_registry: {}\n")

    findings = analyze_schema_registry_config(str(path))

    assert findings[0]["rule_id"] == "schema_registry.config.url.missing"
    assert findings[0]["severity"] == "ERROR"


def test_schema_registry_query_failure_blocks_collection(monkeypatch, tmp_path):
    from beacon import schema_registry_connector

    path = tmp_path / "schema-registry.yaml"
    path.write_text("schema_registry:\n  url: http://schema-registry.local:8081\n")

    def fake_urlopen(request, timeout=None):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(schema_registry_connector.urllib.request, "urlopen", fake_urlopen)

    findings = schema_registry_connector.analyze_schema_registry_config(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "schema_registry.runtime.read_only_mode" in rule_ids
    assert "schema_registry.query.failed" in rule_ids


def test_schema_registry_uses_mtls_context(monkeypatch, tmp_path):
    from beacon import schema_registry_connector

    path = tmp_path / "schema-registry.yaml"
    path.write_text("""
schema_registry:
  url: https://schema-registry.local:8081
  tls:
    ca_cert: /tmp/ca.pem
    client_cert: /tmp/client.pem
    client_key: /tmp/client.key
""")

    calls = []

    class FakeContext:
        def load_cert_chain(self, certfile, keyfile=None):
            calls.append(("load_cert_chain", certfile, keyfile))

    def fake_create_default_context(cafile=None):
        calls.append(("create_default_context", cafile))
        return FakeContext()

    def fake_urlopen(request, timeout=None, context=None):
        calls.append(("urlopen", request.full_url, context is not None))
        if request.full_url.endswith("/subjects"):
            return FakeSchemaRegistryResponse([])
        if request.full_url.endswith("/config"):
            return FakeSchemaRegistryResponse({"compatibilityLevel": "BACKWARD"})
        raise AssertionError(request.full_url)

    monkeypatch.setattr(
        schema_registry_connector.ssl,
        "create_default_context",
        fake_create_default_context,
    )
    monkeypatch.setattr(schema_registry_connector.urllib.request, "urlopen", fake_urlopen)

    findings = schema_registry_connector.analyze_schema_registry_config(str(path))

    assert findings[0]["rule_id"] == "schema_registry.runtime.read_only_mode"
    assert ("create_default_context", "/tmp/ca.pem") in calls
    assert ("load_cert_chain", "/tmp/client.pem", "/tmp/client.key") in calls
    assert any(call[0] == "urlopen" and call[2] for call in calls)
