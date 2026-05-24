import json

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
