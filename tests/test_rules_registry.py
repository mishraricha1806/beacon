import os
import tempfile
import yaml

from beacon import rules_registry


def test_registry_loads_builtin_rule():
    meta = rules_registry.get("kafka.topic.replication_factor.low")
    assert meta is not None
    assert meta.get("category") == "resiliency"


def test_registry_loads_overrides_from_dir(monkeypatch):
    td = tempfile.TemporaryDirectory()
    try:
        # create an override YAML that changes recommendation
        rule = {
            "rule_id": "kafka.topic.replication_factor.low",
            "title": "override title",
            "description": "override",
            "severity_default": "HIGH",
            "category": "resiliency",
            "recommendation": "Use replication_factor=2 for some reason",
        }

        path = os.path.join(td.name, "replication_override.yaml")
        with open(path, "w") as f:
            yaml.safe_dump(rule, f)

        monkeypatch.setenv("BEACON_RULES_METADATA_DIR", td.name)
        rules_registry.reload()

        meta = rules_registry.get("kafka.topic.replication_factor.low")
        assert meta is not None
        assert meta.get("title") == "override title"
        assert meta.get("recommendation").startswith("Use replication_factor=2")
    finally:
        td.cleanup()


# ...existing code...
