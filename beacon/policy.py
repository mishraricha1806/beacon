import os
import yaml
from typing import Dict, Any, Optional

DEFAULT_POLICY_PATH = os.path.expanduser("~/.beacon/policy.yaml")


def load_policy(path: Optional[str] = None) -> Dict[str, Any]:
    """Load a policy file mapping rule_id -> policy settings.

    Policy file format (YAML):
    rules:
      kafka.topic.replication_factor.low:
        enabled: true
        severity: HIGH
      kafka.topic.retention_bytes.missing:
        enabled: false

    Returns the parsed dict, or empty dict when not found/invalid.
    """
    p = path or os.environ.get("BEACON_POLICY_FILE") or DEFAULT_POLICY_PATH

    if not os.path.exists(p):
        return {}

    try:
        with open(p, "r") as f:
            data = yaml.safe_load(f) or {}
            return data.get("rules", {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def apply_policy_to_findings(findings: list, policy: Optional[Dict[str, Any]] = None) -> list:
    """Return a new list of findings after applying policy overrides.

    Policy keys per rule_id:
      enabled: bool (if false, drop the finding)
      severity: override severity string
    """
    if policy is None:
        policy = load_policy()

    out = []

    for f in findings:
        rid = f.get("rule_id")
        if not rid:
            out.append(f)
            continue

        rule_policy = policy.get(rid)

        if rule_policy is None:
            out.append(f)
            continue

        # if explicitly disabled
        if rule_policy.get("enabled") is False:
            continue

        # clone and apply severity override if present
        newf = dict(f)
        sev = rule_policy.get("severity")
        if sev:
            newf["severity"] = sev

        out.append(newf)

    return out
