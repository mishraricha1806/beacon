def finding(
    severity,
    title,
    impact,
    recommendation,
    file,
    rule_id="generic.rule",
    domain="generic",
    category="operational_safety",
    evidence=None,
    tags=None,
):
    return {
        "rule_id": rule_id,
        "domain": domain,
        "category": category,
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence or {},
        "tags": tags or [],
    }
