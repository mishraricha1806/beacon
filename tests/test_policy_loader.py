import os
import tempfile
import yaml

from beacon.policy import load_policy, apply_policy_to_findings


def test_load_policy_nonexistent():
    # no policy file should return empty dict
    p = load_policy(path="/does/not/exist.yaml")
    assert p == {}


def test_apply_policy_disables_and_overrides():
    td = tempfile.TemporaryDirectory()
    try:
        policy = {
            "rules": {
                "kafka.topic.replication_factor.low": {"enabled": False},
                "kafka.topic.retention_bytes.missing": {
                    "enabled": True,
                    "severity": "LOW",
                },
            }
        }

        path = os.path.join(td.name, "policy.yaml")
        with open(path, "w") as f:
            yaml.safe_dump(policy, f)

        p = load_policy(path=path)
        assert "kafka.topic.replication_factor.low" in p

        findings = [
            {"rule_id": "kafka.topic.replication_factor.low", "severity": "CRITICAL"},
            {"rule_id": "kafka.topic.retention_bytes.missing", "severity": "HIGH"},
            {"rule_id": "some.other.rule", "severity": "MEDIUM"},
        ]

        out = apply_policy_to_findings(findings, p)

        # replication factor rule disabled -> removed
        assert all(f["rule_id"] != "kafka.topic.replication_factor.low" for f in out)

        # retention_bytes severity overridden to LOW
        r = next(
            f for f in out if f["rule_id"] == "kafka.topic.retention_bytes.missing"
        )
        assert r["severity"] == "LOW"

        # unrelated rule preserved
        assert any(f["rule_id"] == "some.other.rule" for f in out)

    finally:
        td.cleanup()
