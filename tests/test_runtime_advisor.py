from beacon.runtime_advisor import analyze_runtime_file


def test_runtime_advisor_returns_decision():
    findings = analyze_runtime_file("./examples/runtime/kafka-runtime.yaml")

    assert len(findings) > 0
    assert any("Decision:" in f["title"] for f in findings)