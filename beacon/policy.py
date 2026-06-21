import os
from datetime import date
from fnmatch import fnmatch
from typing import Any, Dict, Optional

import yaml

DEFAULT_POLICY_PATH = os.path.expanduser("~/.beacon/policy.yaml")


SEVERITY_ORDER = {
    "ERROR": 5,
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0,
}


def load_policy_document(path: Optional[str] = None) -> Dict[str, Any]:
    p = path or os.environ.get("BEACON_POLICY_FILE") or DEFAULT_POLICY_PATH

    if not os.path.exists(p):
        return {}

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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
    return load_policy_document(path).get("rules", {})


def load_policy_bundle(path: Optional[str] = None) -> Dict[str, Any]:
    """Load rule overrides, waivers, and CI options from a policy file."""
    data = load_policy_document(path)
    return normalize_policy_bundle(data)


def normalize_policy_bundle(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    policy = data.get("policy") if isinstance(data.get("policy"), dict) else data
    return {
        "rules": policy.get("rules", {}) if isinstance(policy.get("rules"), dict) else {},
        "waivers": policy.get("waivers", []) if isinstance(policy.get("waivers"), list) else [],
        "ci": policy.get("ci", {}) if isinstance(policy.get("ci"), dict) else {},
    }


def merge_policy_bundles(*bundles: Dict[str, Any]) -> Dict[str, Any]:
    merged = {"rules": {}, "waivers": [], "ci": {}}

    for bundle in bundles:
        if not bundle:
            continue
        normalized = normalize_policy_bundle(bundle)
        merged["rules"].update(normalized["rules"])
        merged["waivers"].extend(normalized["waivers"])
        merged["ci"].update(normalized["ci"])

    return merged


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


def apply_policy_bundle_to_findings(
    findings: list,
    bundle: Optional[Dict[str, Any]] = None,
    today: Optional[date] = None,
) -> list:
    """Apply rule overrides and visible waivers to findings.

    Waivers do not hide operational risk. They keep the finding in the report,
    mark it as waived, and downgrade the severity to INFO unless configured
    otherwise.
    """
    bundle = normalize_policy_bundle(bundle)
    out = apply_policy_to_findings(findings, bundle["rules"])

    if not bundle["waivers"]:
        return out

    current_date = today or date.today()
    waived = []
    for finding in out:
        waiver = matching_waiver(finding, bundle["waivers"], current_date)
        if not waiver:
            waived.append(finding)
            continue

        new_finding = dict(finding)
        new_finding["waived"] = True
        new_finding["waiver_reason"] = waiver.get("reason", "Accepted by Beacon policy.")
        if waiver.get("expires"):
            new_finding["waiver_expires"] = str(waiver["expires"])
        new_finding["policy_original_severity"] = finding.get("severity")
        new_finding["severity"] = waiver.get("severity", "INFO")
        waived.append(new_finding)

    return waived


def matching_waiver(finding: Dict[str, Any], waivers: list, current_date: date):
    for waiver in waivers:
        if not isinstance(waiver, dict):
            continue
        if waiver.get("rule_id") != finding.get("rule_id"):
            continue
        if waiver_expired(waiver, current_date):
            continue
        if waiver_resource_matches(finding, waiver):
            return waiver
    return None


def waiver_expired(waiver: Dict[str, Any], current_date: date) -> bool:
    expires = waiver.get("expires")
    if not expires:
        return False
    try:
        expiry_date = expires if isinstance(expires, date) else date.fromisoformat(str(expires))
    except ValueError:
        return True
    return expiry_date < current_date


def waiver_resource_matches(finding: Dict[str, Any], waiver: Dict[str, Any]) -> bool:
    resource = waiver.get("resource")
    resource_pattern = waiver.get("resource_pattern")

    if not resource and not resource_pattern:
        return True

    names = finding_resource_names(finding)
    if resource and resource in names:
        return True
    if resource_pattern and any(fnmatch(name, resource_pattern) for name in names):
        return True
    return False


def finding_resource_names(finding: Dict[str, Any]) -> set:
    names = set()
    evidence = finding.get("evidence") or {}
    if isinstance(evidence, dict):
        for key in ("topic", "name", "resource", "consumer_group", "group_id", "service"):
            value = evidence.get(key)
            if value:
                names.add(str(value))

    for key in ("resource", "file"):
        if finding.get(key):
            names.add(str(finding[key]))

    title = finding.get("title") or ""
    if "'" in title:
        parts = title.split("'")
        for index in range(1, len(parts), 2):
            if parts[index]:
                names.add(parts[index])

    return names


def readiness_exit_code(summary: Dict[str, Any], fail_on: Optional[str] = "critical") -> int:
    """Return CI-friendly exit codes for a readiness summary.

    0 means the configured gate passed, 1 means readiness risk crossed the
    requested threshold, and 2 means Beacon analysis itself was blocked.
    """
    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR" or summary.get("error", 0) > 0:
        return 2

    threshold = (fail_on or "critical").upper()
    if threshold == "NONE":
        return 0
    if threshold not in SEVERITY_ORDER:
        threshold = "CRITICAL"

    threshold_value = SEVERITY_ORDER[threshold]
    for severity, value in SEVERITY_ORDER.items():
        if value >= threshold_value and summary.get(severity.lower(), 0) > 0:
            return 1
    return 0
