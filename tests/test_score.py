from beacon.reporter import calculate_score


def test_critical_reduces_score_more_than_low():
    critical_findings = [
        {
            "severity": "CRITICAL",
            "title": "critical issue",
            "impact": "impact",
            "recommendation": "fix",
            "file": "test",
        }
    ]

    low_findings = [
        {
            "severity": "LOW",
            "title": "low issue",
            "impact": "impact",
            "recommendation": "fix",
            "file": "test",
        }
    ]

    assert calculate_score(critical_findings) < calculate_score(low_findings)


def test_score_never_below_zero():
    findings = []

    for i in range(20):
        findings.append(
            {
                "severity": "CRITICAL",
                "title": f"critical issue {i}",
                "impact": "impact",
                "recommendation": "fix",
                "file": "test",
            }
        )

    assert calculate_score(findings) == 0
