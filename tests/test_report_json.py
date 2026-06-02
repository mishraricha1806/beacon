import json

from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.reporter import print_report


def test_print_report_json_outputs_valid_json(capsys):
    findings = [
        {
            "severity": "HIGH",
            "title": "test issue",
            "impact": "impact",
            "recommendation": "fix",
            "file": "test",
        }
    ]

    # Should not raise
    print_report(findings, html=False, open_report=False, output="json")

    captured = capsys.readouterr()
    out = captured.out.strip()

    assert out, "No output captured from print_report(json)"

    payload = json.loads(out)

    assert "score" in payload
    assert "findings" in payload
    assert payload["findings"] == findings


def test_print_report_json_outputs_diagnostic_summary(capsys):
    findings = [
        {
            "rule_id": "database.runtime.latency.high",
            "domain": "database",
            "category": "runtime_stability",
            "severity": "HIGH",
            "title": "Database latency high",
            "impact": "impact",
            "recommendation": "fix",
            "file": "runtime.yaml",
            "evidence": {},
            "tags": [],
        }
    ]

    print_report(
        findings,
        html=False,
        open_report=False,
        output="json",
        diagnostic_summary=build_diagnostic_summary(findings),
    )

    payload = json.loads(capsys.readouterr().out)

    assert payload["readiness_summary"] is None
    assert payload["diagnostic_summary"]["diagnostic_status"] in {
        "ROOT_CAUSE_CANDIDATES_FOUND",
        "DEGRADATION_SIGNALS_FOUND",
    }
