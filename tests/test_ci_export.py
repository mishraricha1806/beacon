import json
from xml.etree import ElementTree

from beacon.ci_export import build_junit, build_sarif, finding_fingerprint


def finding(severity="HIGH", waived=False):
    return {
        "rule_id": "k8s.workload.probes.missing",
        "domain": "kubernetes",
        "category": "operational_safety",
        "severity": severity,
        "title": "Kubernetes workload missing probes",
        "impact": "Bad pods may receive traffic.",
        "recommendation": "Add readiness and liveness probes.",
        "file": "deployment.yaml",
        "evidence": {"name": "checkout-api", "namespace": "prod"},
        "tags": ["kubernetes", "availability"],
        "waived": waived,
        "waiver_reason": "Temporary migration" if waived else None,
    }


def summary():
    return {
        "production_decision": "NOT READY",
        "score": 70,
        "score_status": "CALCULATED",
        "error": 0,
    }


def test_finding_fingerprint_is_stable_across_dictionary_order():
    first = finding()
    second = finding()
    second["evidence"] = {"namespace": "prod", "name": "checkout-api"}

    assert finding_fingerprint(first) == finding_fingerprint(second)


def test_sarif_contains_rule_location_fingerprint_and_suppression():
    payload = build_sarif([finding(waived=True)], summary())
    result = payload["runs"][0]["results"][0]

    assert payload["version"] == "2.1.0"
    assert result["ruleId"] == "k8s.workload.probes.missing"
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == (
        "deployment.yaml"
    )
    assert len(result["partialFingerprints"]["beaconFindingFingerprint/v1"]) == 64
    assert result["suppressions"][0]["status"] == "accepted"
    json.dumps(payload)


def test_junit_uses_configured_failure_threshold_and_escapes_content():
    findings = [finding("HIGH"), finding("MEDIUM")]
    findings[0]["title"] = "Unsafe <service> & dependency"

    document = build_junit(findings, summary(), fail_on="high")
    suite = ElementTree.fromstring(document)

    assert suite.attrib["tests"] == "2"
    assert suite.attrib["failures"] == "1"
    assert suite.attrib["errors"] == "0"
    assert len(suite.findall("testcase/failure")) == 1
    assert len(suite.findall("testcase/system-out")) == 1
    assert "Unsafe &lt;service&gt;" in document


def test_reusable_action_preserves_artifacts_before_enforcing_gate():
    action = open(".github/actions/beacon-readiness/action.yml", encoding="utf-8").read()

    assert "baseline-evidence:" in action
    assert "beacon-comparison.json" in action
    assert "beacon-comparison.md" in action
    assert "beacon-pack-validation.json" in action
    assert "BEACON_PACK_EXIT_CODE" in action
    assert 'echo "BEACON_EXIT_CODE=${beacon_exit_code}"' in action
    assert action.index("Compare readiness with baseline") < action.index(
        "Enforce configured readiness gate"
    )
