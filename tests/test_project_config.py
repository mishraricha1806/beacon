from pathlib import Path

from beacon.project_config import (
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
readiness:
  include:
    - ./infra
report:
  format:
    - json
tasks:
  prod-check:
    command: readiness
""",
        encoding="utf-8",
    )

    data, config_path = load_project_config(config)

    assert config_path == config.resolve()
    assert config_readiness_includes(data, config_path) == [str(tmp_path / "infra")]
    assert config_report_options(data)["output"] == "json"
    assert sorted(config_tasks(data)) == ["prod-check"]


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
