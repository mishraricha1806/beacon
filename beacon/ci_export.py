"""CI-native exporters for deterministic Beacon readiness findings."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree

from beacon.contracts import engine_metadata, utc_timestamp

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
SEVERITY_ORDER = {
    "ERROR": 0,
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
    "INFO": 5,
}


def finding_fingerprint(finding):
    """Return a stable identity for the same rule, resource, and evidence."""
    identity = {
        "rule_id": finding.get("rule_id"),
        "file": finding.get("file"),
        "evidence": finding.get("evidence") or {},
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_sarif(findings, summary=None):
    engine = engine_metadata()
    rules = {}
    results = []

    for finding in findings:
        rule_id = str(finding.get("rule_id") or "beacon.unknown")
        rules.setdefault(rule_id, sarif_rule(rule_id, finding))
        result = {
            "ruleId": rule_id,
            "level": sarif_level(finding.get("severity")),
            "message": {"text": str(finding.get("title") or rule_id)},
            "partialFingerprints": {
                "beaconFindingFingerprint/v1": finding_fingerprint(finding),
            },
            "properties": {
                "severity": finding.get("severity"),
                "domain": finding.get("domain"),
                "category": finding.get("category"),
                "recommendation": finding.get("recommendation"),
                "waived": finding.get("waived") is True,
            },
        }
        if finding.get("file"):
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": str(finding["file"])},
                    }
                }
            ]
        if finding.get("waived") is True:
            suppression = {"kind": "external", "status": "accepted"}
            if finding.get("waiver_reason"):
                suppression["justification"] = str(finding["waiver_reason"])
            result["suppressions"] = [suppression]
        results.append(result)

    run = {
        "tool": {
            "driver": {
                "name": "Beacon",
                "semanticVersion": engine["version"],
                "informationUri": "https://github.com/mishraricha1806/beacon",
                "rules": [rules[key] for key in sorted(rules)],
            }
        },
        "results": results,
        "invocations": [
            {
                "executionSuccessful": not bool((summary or {}).get("error")),
                "endTimeUtc": utc_timestamp(),
            }
        ],
        "properties": {
            "beaconDecision": (summary or {}).get("production_decision"),
            "beaconScore": (summary or {}).get("score"),
            "beaconScoreStatus": (summary or {}).get("score_status"),
        },
    }
    return {"version": SARIF_VERSION, "$schema": SARIF_SCHEMA, "runs": [run]}


def sarif_rule(rule_id, finding):
    rule = {
        "id": rule_id,
        "shortDescription": {"text": str(finding.get("title") or rule_id)},
        "defaultConfiguration": {"level": sarif_level(finding.get("severity"))},
        "properties": {
            "domain": finding.get("domain"),
            "category": finding.get("category"),
            "tags": list(finding.get("tags") or []),
        },
    }
    if finding.get("impact"):
        rule["fullDescription"] = {"text": str(finding["impact"])}
    if finding.get("recommendation"):
        rule["help"] = {"text": str(finding["recommendation"])}
    return rule


def sarif_level(severity):
    severity = str(severity or "INFO").upper()
    if severity in {"ERROR", "CRITICAL", "HIGH"}:
        return "error"
    if severity in {"MEDIUM", "LOW"}:
        return "warning"
    return "note"


def build_junit(findings, summary=None, fail_on="high"):
    threshold = severity_threshold(fail_on)
    suite = ElementTree.Element(
        "testsuite",
        {
            "name": "Beacon readiness",
            "tests": str(len(findings)),
            "failures": str(
                sum(
                    1
                    for item in findings
                    if str(item.get("severity")).upper() != "ERROR"
                    and finding_fails(item, threshold)
                )
            ),
            "errors": str(
                sum(
                    1
                    for item in findings
                    if str(item.get("severity")).upper() == "ERROR"
                )
            ),
            "timestamp": utc_timestamp(),
        },
    )
    properties = ElementTree.SubElement(suite, "properties")
    for name, value in (
        ("beacon.decision", (summary or {}).get("production_decision")),
        ("beacon.score", (summary or {}).get("score")),
        ("beacon.score_status", (summary or {}).get("score_status")),
        ("beacon.fail_on", fail_on),
    ):
        ElementTree.SubElement(
            properties,
            "property",
            {"name": name, "value": "" if value is None else str(value)},
        )

    for finding in findings:
        case = ElementTree.SubElement(
            suite,
            "testcase",
            {
                "classname": str(finding.get("domain") or "beacon.readiness"),
                "name": str(finding.get("rule_id") or finding.get("title") or "finding"),
                "file": str(finding.get("file") or ""),
            },
        )
        details = junit_details(finding)
        severity = str(finding.get("severity") or "INFO").upper()
        if severity == "ERROR":
            node = ElementTree.SubElement(case, "error", {"message": str(finding.get("title"))})
            node.text = details
        elif finding_fails(finding, threshold):
            node = ElementTree.SubElement(
                case,
                "failure",
                {"message": str(finding.get("title")), "type": severity},
            )
            node.text = details
        else:
            ElementTree.SubElement(case, "system-out").text = details

    return ElementTree.tostring(suite, encoding="unicode", xml_declaration=True)


def junit_details(finding):
    return "\n".join(
        value
        for value in (
            f"Severity: {finding.get('severity')}",
            f"Impact: {finding.get('impact')}" if finding.get("impact") else None,
            (
                f"Recommendation: {finding.get('recommendation')}"
                if finding.get("recommendation")
                else None
            ),
            f"Fingerprint: {finding_fingerprint(finding)}",
        )
        if value
    )


def severity_threshold(fail_on):
    normalized = str(fail_on or "high").lower()
    if normalized == "none":
        return -1
    if normalized not in {"critical", "high", "medium", "low"}:
        raise ValueError("fail_on must be one of: none, critical, high, medium, low")
    return SEVERITY_ORDER[normalized.upper()]


def finding_fails(finding, threshold):
    if threshold < 0:
        return False
    severity = str(finding.get("severity") or "INFO").upper()
    return SEVERITY_ORDER.get(severity, SEVERITY_ORDER["INFO"]) <= threshold


def write_ci_artifacts(findings, summary, sarif_output=None, junit_output=None, fail_on="high"):
    if sarif_output:
        write_text(
            sarif_output,
            json.dumps(build_sarif(findings, summary), indent=2) + "\n",
        )
    if junit_output:
        write_text(junit_output, build_junit(findings, summary, fail_on=fail_on) + "\n")


def write_text(path, content):
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
