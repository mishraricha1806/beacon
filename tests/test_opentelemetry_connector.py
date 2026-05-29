def test_opentelemetry_export_maps_to_runtime_findings(tmp_path):
    from beacon.opentelemetry_connector import analyze_opentelemetry_file

    path = tmp_path / "otel.yaml"
    path.write_text(
        """
opentelemetry:
  flow:
    name: checkout
  spans:
    - trace_id: t1
      service: checkout-api
      duration_ms: 1500
      status: ERROR
      attributes:
        http.status_code: 503
        error.type: timeout
        retry: true
        deployment.recent: true
    - trace_id: t2
      service: checkout-api
      duration_ms: 1200
      status: OK
      attributes:
        retry: true
    - trace_id: t1
      service: orders-db
      duration_ms: 800
      status: OK
      attributes:
        db.system: postgres
        db.name: orders-db
  metrics:
    - name: kafka.consumer_lag_increasing
      value: 1
    - name: consumer.retry_rate_percent
      value: 12
    - name: database.connection_pool_utilization_percent
      database: orders-db
      value: 91
    - name: storage.backup_age_hours
      resource: orders-volume
      value: 36
"""
    )

    findings = analyze_opentelemetry_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "opentelemetry.runtime.read_only_mode" in rule_ids
    assert "api.runtime.latency_p95.high" in rule_ids
    assert "api.runtime.deployment_correlated_degradation" in rule_ids
    assert "database.runtime.connection_pool.exhaustion" in rule_ids
    assert "flow.runtime.downstream_db_bottleneck" in rule_ids
    assert "storage.runtime.backup_stale" in rule_ids


def test_opentelemetry_missing_runtime_signals_blocks_analysis(tmp_path):
    from beacon.opentelemetry_connector import analyze_opentelemetry_file

    path = tmp_path / "empty-otel.yaml"
    path.write_text("opentelemetry: {}\n")

    findings = analyze_opentelemetry_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "opentelemetry.runtime.signals.missing" in rule_ids


def test_opentelemetry_json_export_is_supported(tmp_path):
    import json

    from beacon.opentelemetry_connector import analyze_opentelemetry_file

    path = tmp_path / "otel.json"
    path.write_text(
        json.dumps(
            {
                "opentelemetry": {
                    "spans": [
                        {
                            "service": "checkout-api",
                            "duration_ms": 1300,
                            "status": "ERROR",
                            "attributes": {
                                "http.status_code": "503",
                                "error.type": "timeout",
                                "deployment.recent": True,
                            },
                        }
                    ]
                }
            }
        )
    )

    findings = analyze_opentelemetry_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "opentelemetry.runtime.read_only_mode" in rule_ids
    assert "api.runtime.latency_p95.high" in rule_ids
    assert "api.runtime.error_rate.high" in rule_ids
