def calculate_readiness(findings):
    summary = {
        "score": 100,
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "survivability": "LOW RISK",
        "categories": {
            "resiliency": {"risk": "LOW RISK", "findings": 0},
            "scalability": {"risk": "LOW RISK", "findings": 0},
            "storage_sustainability": {"risk": "LOW RISK", "findings": 0},
            "operational_safety": {"risk": "LOW RISK", "findings": 0},
            "recovery_readiness": {"risk": "LOW RISK", "findings": 0},
        },
        "business_summary": "",
        "recommended_action": ""
    }

    for finding in findings:
        severity = finding["severity"]
        title = finding["title"].lower()
        impact = finding["impact"].lower()

        if severity == "CRITICAL":
            summary["critical"] += 1
            summary["score"] -= 20
        elif severity == "HIGH":
            summary["high"] += 1
            summary["score"] -= 10
        elif severity == "MEDIUM":
            summary["medium"] += 1
            summary["score"] -= 5
        elif severity == "LOW":
            summary["low"] += 1
            summary["score"] -= 2

        category = classify_finding(title, impact)

        if category:
            summary["categories"][category]["findings"] += 1

    summary["score"] = max(0, summary["score"])
    summary["survivability"] = determine_risk(summary["score"])

    for category, data in summary["categories"].items():
        data["risk"] = determine_category_risk(data["findings"])

    summary["business_summary"] = build_business_summary(summary)
    summary["recommended_action"] = build_recommended_action(summary)

    return summary


def classify_finding(title, impact):
    text = f"{title} {impact}"

    if any(word in text for word in [
        "replication", "broker failure", "min.insync", "under-replicated", "availability"
    ]):
        return "resiliency"

    if any(word in text for word in [
        "partition", "parallelism", "throughput", "consumer lag", "scalability"
    ]):
        return "scalability"

    if any(word in text for word in [
        "retention", "disk", "storage", "segment", "cleanup", "message size"
    ]):
        return "storage_sustainability"

    if any(word in text for word in [
        "public", "iam", "permission", "encryption", "access", "wildcard", "tags"
    ]):
        return "operational_safety"

    if any(word in text for word in [
        "replay", "recovery", "versioning", "overwrite", "delete"
    ]):
        return "recovery_readiness"

    return "operational_safety"


def determine_risk(score):
    if score >= 85:
        return "LOW RISK"
    if score >= 70:
        return "MEDIUM RISK"
    if score >= 50:
        return "HIGH RISK"
    return "CRITICAL RISK"


def determine_category_risk(count):
    if count == 0:
        return "LOW RISK"
    if count <= 2:
        return "MEDIUM RISK"
    if count <= 4:
        return "HIGH RISK"
    return "CRITICAL RISK"


def build_business_summary(summary):
    risk = summary["survivability"]

    if risk == "LOW RISK":
        return "The system appears broadly production ready based on current analyzed signals."

    if risk == "MEDIUM RISK":
        return "The system has some production-readiness concerns that should be reviewed before rollout."

    if risk == "HIGH RISK":
        return "The system has significant operational risks that may affect production stability under failure or traffic growth."

    return "The system has critical production-readiness gaps and should not be considered safe for production without remediation."


def build_recommended_action(summary):
    if summary["critical"] > 0:
        return "Resolve all critical findings before production rollout."

    if summary["high"] > 0:
        return "Review and fix high-risk operational findings before production approval."

    if summary["medium"] > 0:
        return "Address medium-risk findings or document accepted operational risk."

    return "Continue with standard production review and monitoring."