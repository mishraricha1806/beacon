import os
import tempfile
from pathlib import Path
import yaml

from beacon.engine.registry import registry
from beacon.engine import metadata_registry as rules_registry


def test_registry_loads_builtin_rule():
    meta = rules_registry.get("kafka.topic.replication_factor.low")
    assert meta is not None
    assert meta.get("category") == "resiliency"


def test_registry_covers_all_registered_rules():
    rules_registry.reload()
    metadata = rules_registry.list_rules()
    registered_rule_ids = {rule.rule_id for rule in registry.get_all()}

    assert registered_rule_ids
    assert registered_rule_ids <= set(metadata)


def test_registered_rules_have_curated_yaml_metadata():
    metadata_dir = Path("beacon/rules/metadata")
    curated_rule_ids = set()
    for path in metadata_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text()) or {}
        if isinstance(data, dict) and data.get("rule_id"):
            curated_rule_ids.add(data["rule_id"])

    registered_rule_ids = {rule.rule_id for rule in registry.get_all()}

    assert registered_rule_ids <= curated_rule_ids


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
