from beacon.scanner import scan_path
from beacon.readiness.kafka.readiness_engine import calculate_readiness


def test_bad_infra_is_not_production_ready():
    findings = scan_path("./examples/bad-infra")
    summary = calculate_readiness(findings)

    assert summary["production_decision"] == "NOT READY"
    assert summary["score"] < 70
    assert len(findings) > 0
