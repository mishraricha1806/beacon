from beacon.scanner import scan_path


def test_scan_bad_infra_returns_findings():
    findings = scan_path("./examples/bad-infra")

    assert len(findings) > 0
    assert any(f["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] for f in findings)


def test_scan_missing_path_returns_error():
    findings = scan_path("./missing-path")

    assert len(findings) == 1
    assert findings[0]["severity"] == "ERROR"
