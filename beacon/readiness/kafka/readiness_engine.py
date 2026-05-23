def calculate_readiness(findings):
    score = 100

    critical = 0
    high = 0
    medium = 0
    low = 0

    for finding in findings:
        severity = finding["severity"]

        if severity == "CRITICAL":
            critical += 1
            score -= 20

        elif severity == "HIGH":
            high += 1
            score -= 10

        elif severity == "MEDIUM":
            medium += 1
            score -= 5

        elif severity == "LOW":
            low += 1
            score -= 2

    score = max(0, score)

    survivability = determine_survivability(score)

    return {
        "score": score,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "survivability": survivability,
    }


def determine_survivability(score):
    if score >= 85:
        return "LOW RISK"

    if score >= 70:
        return "MEDIUM RISK"

    if score >= 50:
        return "HIGH RISK"

    return "CRITICAL RISK"