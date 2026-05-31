from beacon.engine.static_evaluator import (
    evaluate_kafka_config,
    evaluate_terraform_config,
)


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


__all__ = [
    "finding",
    "evaluate_kafka_config",
    "evaluate_terraform_config",
]
