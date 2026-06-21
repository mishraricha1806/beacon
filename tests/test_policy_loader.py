import os
import tempfile
from datetime import date

import yaml

from beacon.policy import (
    apply_policy_bundle_to_findings,
    apply_policy_to_findings,
    load_policy,
    readiness_exit_code,
)


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
        r = next(f for f in out if f["rule_id"] == "kafka.topic.retention_bytes.missing")
        assert r["severity"] == "LOW"

        # unrelated rule preserved
        assert any(f["rule_id"] == "some.other.rule" for f in out)

    finally:
        td.cleanup()


def test_policy_waiver_marks_finding_visible_and_downgrades():
    findings = [
        {
            "rule_id": "kafka.topic.partitions.low",
            "severity": "HIGH",
            "title": "Kafka topic 'orders.retry' has low partition count",
            "evidence": {"topic": "orders.retry"},
        }
    ]

    out = apply_policy_bundle_to_findings(
        findings,
        {
            "waivers": [
                {
                    "rule_id": "kafka.topic.partitions.low",
                    "resource_pattern": "*.retry",
                    "reason": "Retry topics preserve ordering.",
                    "expires": "2026-12-31",
                }
            ]
        },
        today=date(2026, 6, 20),
    )

    assert out[0]["waived"] is True
    assert out[0]["severity"] == "INFO"
    assert out[0]["policy_original_severity"] == "HIGH"
    assert out[0]["waiver_reason"] == "Retry topics preserve ordering."


def test_expired_policy_waiver_does_not_apply():
    findings = [
        {
            "rule_id": "kafka.topic.partitions.low",
            "severity": "HIGH",
            "title": "Kafka topic 'orders.retry' has low partition count",
            "evidence": {"topic": "orders.retry"},
        }
    ]

    out = apply_policy_bundle_to_findings(
        findings,
        {
            "waivers": [
                {
                    "rule_id": "kafka.topic.partitions.low",
                    "resource": "orders.retry",
                    "expires": "2026-01-01",
                }
            ]
        },
        today=date(2026, 6, 20),
    )

    assert out[0]["severity"] == "HIGH"
    assert "waived" not in out[0]


def test_readiness_exit_code_respects_thresholds_and_blocked_state():
    assert readiness_exit_code({"critical": 0, "high": 1, "error": 0}, "critical") == 0
    assert readiness_exit_code({"critical": 0, "high": 1, "error": 0}, "high") == 1
    assert readiness_exit_code({"critical": 0, "high": 1, "error": 0}, "none") == 0
    assert readiness_exit_code({"critical": 0, "high": 0, "error": 1}, "none") == 2
