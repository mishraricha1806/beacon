from pathlib import Path

from beacon.project_config import (
    config_ci_options,
    config_environment,
    config_environment_model,
    config_live_inputs,
    config_policy_bundle,
    config_policy_path,
    config_readiness_includes,
    config_report_options,
    config_tasks,
    discover_config,
    load_project_config,
    resolve_config_path,
    starter_config,
)


def test_discovers_beacon_yaml_from_parent_directory(tmp_path):
    config = tmp_path / "beacon.yaml"
    config.write_text("project: demo\n", encoding="utf-8")
    nested = tmp_path / "service" / "api"
    nested.mkdir(parents=True)

    assert discover_config(nested) == config


def test_loads_project_config_and_resolves_relative_paths(tmp_path):
    config = tmp_path / "beacon.yaml"
    config.write_text(
        """
project: payments
environment:
  name: prod-us-east
  profile: prod
  criticality: high
  business_flows:
    - checkout
  services:
    - api
  dependencies:
    kafka:
      clusters:
        - events
readiness:
  include:
    - ./infra
live:
  runtime:
    snapshot: ./runtime/all.yaml
  kafka:
    history: ./kafka/history.yaml
report:
  format:
    - json
tasks:
  prod-check:
    command: readiness
policy:
  file: ./policy.yaml
  waivers:
    - rule_id: kafka.topic.partitions.low
      resource_pattern: "*.retry"
      reason: Ordered retry topics.
ci:
  enabled: true
  fail_on: high
""",
        encoding="utf-8",
    )

    data, config_path = load_project_config(config)

    assert config_path == config.resolve()
    assert config_environment(data) == "prod"
    environment_model = config_environment_model(data)
    assert environment_model["criticality"] == "high"
    assert environment_model["service_count"] == 1
    assert environment_model["dependency_domains"] == ["kafka"]
    assert config_readiness_includes(data, config_path) == [str(tmp_path / "infra")]
    live_inputs = config_live_inputs(data, config_path)
    assert live_inputs["snapshot_path"] == str(tmp_path / "runtime" / "all.yaml")
    assert live_inputs["kafka_history_path"] == str(tmp_path / "kafka" / "history.yaml")
    assert config_report_options(data)["output"] == "json"
    assert sorted(config_tasks(data)) == ["prod-check"]
    assert config_policy_path(data, config_path) == str(tmp_path / "policy.yaml")
    policy_bundle = config_policy_bundle(data)
    assert policy_bundle["waivers"][0]["rule_id"] == "kafka.topic.partitions.low"
    assert config_ci_options(data)["fail_on"] == "high"


def test_resolve_config_path_preserves_absolute_paths(tmp_path):
    config_path = tmp_path / "beacon.yaml"
    absolute = str(Path("/tmp/example").resolve())

    assert resolve_config_path(config_path, absolute) == absolute
    assert resolve_config_path(config_path, "./infra") == str(tmp_path / "infra")


def test_starter_config_contains_safe_beacon_tasks():
    config = starter_config()

    assert "command: readiness" in config
    assert "command: diagnose kafka-runtime" in config
    assert "beacon-demo" in config
    assert "business_flows" in config
    assert "waivers:" in config
    assert "fail_on: critical" in config


def test_readiness_summary_includes_environment_model():
    from beacon.readiness.kafka.readiness_engine import calculate_readiness

    summary = calculate_readiness(
        [
            {
                "rule_id": "api.runtime.latency_p95.high",
                "domain": "api",
                "category": "runtime_stability",
                "severity": "HIGH",
                "title": "API latency high",
                "impact": "Requests are slow.",
                "recommendation": "Inspect downstream dependencies.",
                "file": "runtime.yaml",
            }
        ],
        environment="prod",
        environment_model={
            "name": "prod-us-east",
            "profile": "prod",
            "criticality": "high",
            "business_flows": ["checkout"],
            "services": ["api"],
            "service_count": 1,
            "dependencies": {"database": {}, "kafka": {}},
            "dependency_domains": ["database", "kafka"],
            "rto": "30m",
            "rpo": "5m",
        },
    )

    environment = summary["environment_readiness"]
    assert environment["name"] == "prod-us-east"
    assert environment["criticality"] == "high"
    assert environment["business_flows"] == ["checkout"]
    assert environment["blocked_dimensions"]
