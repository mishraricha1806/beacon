def finding(
    rule_id,
    domain,
    category,
    severity,
    title,
    impact,
    recommendation,
    file,
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
