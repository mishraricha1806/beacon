SEVERITY_PENALTIES = {
    "CRITICAL": 20,
    "HIGH": 12,
    "MEDIUM": 7,
    "LOW": 3,
    "ERROR": 5,
    "INFO": 0,
}

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "ERROR", "INFO")


def calculate_score(findings):
    penalty = 0

    for finding in findings:
        penalty += SEVERITY_PENALTIES.get(finding.get("severity"), 0)

    return max(0, 100 - penalty)


def count_severities(findings):
    counts = {severity.lower(): 0 for severity in SEVERITIES}

    for finding in findings:
        severity = finding.get("severity")

        if severity in SEVERITIES:
            counts[severity.lower()] += 1

    return counts


def production_readiness_decision(findings, score):
    counts = count_severities(findings)

    if counts["error"] > 0 or counts["critical"] > 0 or score < 50:
        return "NOT READY"

    if counts["high"] > 0 or score < 70:
        return "READY WITH MAJOR RISKS"

    if counts["medium"] > 0 or score < 85:
        return "READY WITH CONDITIONS"

    return "READY"
