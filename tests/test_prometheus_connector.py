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


class FakeVectorResponse:
    def __init__(self, values, label="broker"):
        self.values = values
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        result = [
            {
                "metric": {self.label: str(key)},
                "value": [1234567890, str(value)],
            }
            for key, value in self.values.items()
        ]
        payload = {"status": "success", "data": {"result": result}}
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


def test_prometheus_kafka_jmx_metrics_map_to_kafka_runtime_findings(monkeypatch, tmp_path):
    from beacon import prometheus_connector

    config = """
prometheus:
  url: http://prometheus.local
  kafka_runtime:
    broker_count: 3
    partition_count: 200
    replication_factor: 3
    replay_target_hours: 2
    retention_remaining_hours: 4
    queries:
      broker_disk_usage_percent: kafka_disk_usage
      broker_disk_usage_by_broker:
        query: kafka_disk_by_broker
        type: map
        label: broker
      under_min_isr_partitions: kafka_under_min_isr
      under_replicated_partitions: kafka_under_replicated
      offline_partitions: kafka_offline
      leader_imbalance_percent: kafka_leader_imbalance
      active_controller_count: kafka_active_controllers
      controller_change_count_15m: kafka_controller_changes
      partition_reassignment_count: kafka_reassignments
      replication_fetcher_lag: kafka_replication_fetcher_lag
      producer_error_rate_percent: kafka_producer_errors
      request_latency_p95_ms: kafka_request_latency
      request_queue_utilization_percent: kafka_request_queue
      network_io_utilization_percent: kafka_network
      produce_throttle_time_ms: kafka_produce_throttle
      fetch_throttle_time_ms: kafka_fetch_throttle
      schema_registry_available:
        query: schema_registry_up
        type: bool
      schema_incompatible_changes_24h: schema_incompatible
      backlog_messages: kafka_backlog
      consumer_throughput_messages_per_sec: kafka_consumer_rate
      producer_rate_messages_per_sec: kafka_producer_rate
"""
    path = tmp_path / "kafka-prometheus.yaml"
    path.write_text(config)

    values = {
        "kafka_disk_usage": 88,
        "kafka_under_min_isr": 2,
        "kafka_under_replicated": 2,
        "kafka_offline": 1,
        "kafka_leader_imbalance": 55,
        "kafka_active_controllers": 2,
        "kafka_controller_changes": 4,
        "kafka_reassignments": 2,
        "kafka_replication_fetcher_lag": 15000,
        "kafka_producer_errors": 7,
        "kafka_request_latency": 700,
        "kafka_request_queue": 86,
        "kafka_network": 92,
        "kafka_produce_throttle": 140,
        "kafka_fetch_throttle": 160,
        "schema_registry_up": 0,
        "schema_incompatible": 1,
        "kafka_backlog": 1000000,
        "kafka_consumer_rate": 100,
        "kafka_producer_rate": 50,
    }

    def fake_urlopen(url, timeout=None):
        if "kafka_disk_by_broker" in url:
            return FakeVectorResponse({"1": 94, "2": 62, "3": 60})
        for query, value in values.items():
            if query in url:
                return FakeResponse(value)
        raise AssertionError(url)

    monkeypatch.setattr(prometheus_connector.urllib.request, "urlopen", fake_urlopen)

    findings = prometheus_connector.analyze_prometheus_config(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "prometheus.runtime.read_only_mode" in rule_ids
    assert "kafka.runtime.broker_disk_skew.critical" in rule_ids
    assert "kafka.runtime.offline_partitions" in rule_ids
    assert "kafka.runtime.under_min_isr_partitions" in rule_ids
    assert "kafka.runtime.under_replicated_partitions" in rule_ids
    assert "kafka.runtime.leader_imbalance.high" in rule_ids
    assert "kafka.runtime.controller_count.invalid" in rule_ids
    assert "kafka.runtime.controller_churn.high" in rule_ids
    assert "kafka.runtime.partition_reassignment.active" in rule_ids
    assert "kafka.runtime.replication_fetcher_lag.high" in rule_ids
    assert "kafka.runtime.producer_error_rate.high" in rule_ids
    assert "kafka.runtime.request_latency.high" in rule_ids
    assert "kafka.runtime.request_queue_saturation.high" in rule_ids
    assert "kafka.runtime.network_saturation.high" in rule_ids
    assert "kafka.runtime.producer_throttle.high" in rule_ids
    assert "kafka.runtime.fetch_throttle.high" in rule_ids
    assert "kafka.runtime.schema_registry.unavailable" in rule_ids
    assert "kafka.runtime.schema_incompatible_changes" in rule_ids
    assert "kafka.runtime.replay.time_exceeds_target" in rule_ids
    assert "kafka.runtime.replay.retention_window_insufficient" in rule_ids
