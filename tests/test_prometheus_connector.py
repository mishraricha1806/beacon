import json


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        payload = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "value": [1234567890, str(self.value)],
                    }
                ]
            },
        }
        return json.dumps(payload).encode("utf-8")


def test_prometheus_config_maps_queries_to_runtime_findings(monkeypatch, tmp_path):
    from beacon import prometheus_connector

    config = """
prometheus:
  url: http://prometheus.local
  api_runtime:
    services:
      - name: checkout-api
        queries:
          latency_p95_ms: api_latency
          error_rate_percent: api_errors
          timeout_rate_percent: api_timeouts
          retry_rate_percent: api_retries
          recent_deployment:
            query: deploy_changes
            type: bool
  database_runtime:
    databases:
      - name: orders-db
        engine: postgres
        queries:
          latency_ms: db_latency
          connection_pool_utilization_percent: db_pool
          lock_waits_high:
            query: db_locks
            type: bool
          replication_lag_seconds: db_lag
          storage_used_percent: db_storage
  storage_runtime:
    resources:
      - name: orders-volume
        type: block_volume
        queries:
          used_percent: storage_used
          growth_percent_7d: storage_growth
          iops_saturation_percent: storage_iops
          backup_age_hours: backup_age
"""
    path = tmp_path / "prometheus.yaml"
    path.write_text(config)

    values = {
        "api_latency": 1400,
        "api_errors": 6,
        "api_timeouts": 4,
        "api_retries": 14,
        "deploy_changes": 1,
        "db_latency": 720,
        "db_pool": 92,
        "db_locks": 1,
        "db_lag": 120,
        "db_storage": 88,
        "storage_used": 91,
        "storage_growth": 26,
        "storage_iops": 89,
        "backup_age": 36,
    }

    def fake_urlopen(url, timeout=None):
        for query, value in values.items():
            if query in url:
                return FakeResponse(value)
        raise AssertionError(url)

    monkeypatch.setattr(prometheus_connector.urllib.request, "urlopen", fake_urlopen)

    findings = prometheus_connector.analyze_prometheus_config(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "prometheus.runtime.read_only_mode" in rule_ids
    assert "api.runtime.retry_amplification" in rule_ids
    assert "database.runtime.connection_pool.exhaustion" in rule_ids
    assert "storage.runtime.backup_stale" in rule_ids


def test_prometheus_missing_url_blocks_analysis(tmp_path):
    from beacon.prometheus_connector import analyze_prometheus_config

    path = tmp_path / "prometheus.yaml"
    path.write_text("prometheus: {}\n")

    findings = analyze_prometheus_config(str(path))

    assert findings[0]["rule_id"] == "prometheus.config.url.missing"
    assert findings[0]["severity"] == "ERROR"
