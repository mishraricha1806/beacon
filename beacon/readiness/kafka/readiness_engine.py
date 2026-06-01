from beacon.scoring import (
    count_severities,
    production_readiness_decision,
)
from beacon.correlations.root_cause import correlate_findings
from beacon.intelligence.context import context_summary
from beacon.kafka_report import build_kafka_report
from beacon.readiness.interpretation import (
    build_business_categories,
    interpret_findings,
    readiness_score_from_points,
    sort_findings,
)


DEFAULT_CATEGORIES = {
    "resiliency": {"risk": "LOW RISK", "findings": 0},
    "scalability": {"risk": "LOW RISK", "findings": 0},
    "storage_sustainability": {"risk": "LOW RISK", "findings": 0},
    "operational_safety": {"risk": "LOW RISK", "findings": 0},
    "recovery_readiness": {"risk": "LOW RISK", "findings": 0},
    "runtime_stability": {"risk": "LOW RISK", "findings": 0},
}


def calculate_readiness(findings, environment=None, intelligence_context=None):
    interpretation = interpret_findings(
        findings,
        environment=environment,
        intelligence_context=intelligence_context,
    )
    interpreted_findings = interpretation["findings"]
    score_findings = interpretation["score_findings"]
    risk_points = interpretation["risk_points"]
    severity_counts = count_severities(interpreted_findings)
    raw_severity_counts = count_severities(findings)

    summary = {
        "score": readiness_score_from_points(risk_points),
        "risk_points": risk_points,
        "scoring_model": {
            "CRITICAL": 100,
            "HIGH": 50,
            "MEDIUM": 20,
            "LOW": 5,
            "INFO": 0,
            "ERROR": 100,
        },
        "score_formula": "100 - min(100, round(risk_points / 2)); any critical/error finding still blocks readiness",
        "score_status": "CALCULATED",
        "critical": severity_counts["critical"],
        "high": severity_counts["high"],
        "medium": severity_counts["medium"],
        "low": severity_counts["low"],
        "error": severity_counts["error"],
        "info": severity_counts["info"],
        "raw_critical": raw_severity_counts["critical"],
        "raw_high": raw_severity_counts["high"],
        "raw_medium": raw_severity_counts["medium"],
        "raw_low": raw_severity_counts["low"],
        "raw_error": raw_severity_counts["error"],
        "raw_info": raw_severity_counts["info"],
        "environment": interpretation["environment"],
        "intelligence_context": context_summary(intelligence_context),
        "interpreted_findings": sort_findings(interpreted_findings),
        "grouped_risks": interpretation["grouped_risks"],
        "business_categories": build_business_categories(
            score_findings, interpretation["grouped_risks"]
        ),
        "suppressed_duplicate_count": max(0, len(findings) - len(score_findings)),
        "survivability": "LOW RISK",
        "categories": {key: dict(value) for key, value in DEFAULT_CATEGORIES.items()},
        "business_summary": "",
        "recommended_action": "",
        "production_decision": "",
        "primary_risk_area": "",
        "top_reasons": [],
        "next_best_actions": [],
        "root_cause_hypotheses": [],
        "kafka_report": None,
    }

    for finding in score_findings:
        if finding.get("severity") == "INFO":
            continue

        category = finding.get("category", "operational_safety")

        if category:
            summary["categories"].setdefault(
                category,
                {"risk": "LOW RISK", "findings": 0},
            )
            summary["categories"][category]["findings"] += 1

    summary["survivability"] = (
        "ANALYSIS BLOCKED" if summary["error"] > 0 else determine_risk(summary["score"])
    )
    if summary["error"] > 0:
        summary["score_status"] = "BLOCKED_BY_ANALYSIS_ERROR"

    for category, data in summary["categories"].items():
        data["risk"] = determine_category_risk(data["findings"])

    summary["business_summary"] = build_business_summary(summary)
    summary["recommended_action"] = build_recommended_action(summary)
    summary["primary_risk_area"] = determine_primary_risk_area(summary)
    summary["production_decision"] = determine_production_decision(summary)
    summary["top_reasons"] = build_top_reasons(
        interpreted_findings, summary["grouped_risks"]
    )
    summary["next_best_actions"] = build_next_best_actions(summary)
    summary["root_cause_hypotheses"] = correlate_findings(interpreted_findings)
    summary["kafka_report"] = build_kafka_report(sort_findings(interpreted_findings))
    return summary


def classify_finding(title, impact):
    text = f"{title} {impact}"

    if any(
        word in text
        for word in [
            "replication",
            "broker failure",
            "min.insync",
            "under-replicated",
            "availability",
        ]
    ):
        return "resiliency"

    if any(
        word in text
        for word in [
            "partition",
            "parallelism",
            "throughput",
            "consumer lag",
            "scalability",
        ]
    ):
        return "scalability"

    if any(
        word in text
        for word in [
            "retention",
            "disk",
            "storage",
            "segment",
            "cleanup",
            "message size",
        ]
    ):
        return "storage_sustainability"

    if any(
        word in text
        for word in [
            "public",
            "iam",
            "permission",
            "encryption",
            "access",
            "wildcard",
            "tags",
        ]
    ):
        return "operational_safety"

    if any(
        word in text
        for word in ["replay", "recovery", "versioning", "overwrite", "delete"]
    ):
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
    if summary["error"] > 0:
        return "Beacon could not complete a production-readiness decision because one or more analysis errors must be resolved."

    if summary.get("environment") != "prod" and summary.get("grouped_risks"):
        return (
            f"Beacon detected risks in a {summary['environment']} environment. "
            "Readiness is based on grouped root-cause signals, with repeated derivative findings de-emphasized."
        )

    risk = summary["survivability"]

    if risk == "LOW RISK":
        return "The system appears broadly production ready based on current analyzed signals."

    if risk == "MEDIUM RISK":
        return "The system has some production-readiness concerns that should be reviewed before rollout."

    if risk == "HIGH RISK":
        return "The system has significant operational risks that may affect production stability under failure or traffic growth."

    return "The system has critical production-readiness gaps and should not be considered safe for production without remediation."


def build_recommended_action(summary):
    if summary["error"] > 0:
        return "Resolve analysis errors, then rerun Beacon before making a production readiness decision."

    if summary["critical"] > 0:
        return "Resolve all critical findings before production rollout."

    if summary["high"] > 0:
        return (
            "Review and fix high-risk operational findings before production approval."
        )

    if summary["medium"] > 0:
        return "Address medium-risk findings or document accepted operational risk."

    return "Continue with standard production review and monitoring."


def determine_primary_risk_area(summary):
    categories = summary["categories"]

    highest = max(categories.items(), key=lambda item: item[1]["findings"])

    if highest[1]["findings"] == 0:
        return "None"

    return highest[0].replace("_", " ").title()


def determine_production_decision(summary):
    findings = []

    for severity in ("error", "critical", "high", "medium", "low", "info"):
        findings.extend(
            {"severity": severity.upper()} for _ in range(summary[severity])
        )

    return production_readiness_decision(findings, summary["score"])


def build_top_reasons(findings, grouped_risks=None):
    reasons = []

    for risk in grouped_risks or []:
        affected = risk.get("affected_count", 0)
        suffix = f" ({affected} affected)" if affected else ""
        reasons.append(f"{risk['severity']}: {risk['title']}{suffix}")

    grouped_titles = {risk["title"] for risk in grouped_risks or []}
    for finding in sort_findings(findings):
        reason = f"{finding['severity']}: {finding['title']}"
        if finding.get("title") in grouped_titles:
            continue
        if reason not in reasons:
            reasons.append(reason)
        if len(reasons) >= 5:
            break

    return reasons[:5]


def build_next_best_actions(summary):
    actions = []

    if summary["error"] > 0:
        actions.append("Resolve Beacon analysis errors and rerun the readiness check.")

    if summary["critical"] > 0:
        actions.append("Resolve all critical production-readiness gaps before rollout.")

    if summary["categories"]["resiliency"]["risk"] in ["HIGH RISK", "CRITICAL RISK"]:
        actions.append(
            "Fix resiliency risks such as replication, broker failure tolerance, and min ISR configuration."
        )

    if summary["categories"]["storage_sustainability"]["risk"] in [
        "HIGH RISK",
        "CRITICAL RISK",
    ]:
        actions.append(
            "Review storage growth controls such as retention_bytes, cleanup policy, segment size, and message size."
        )

    if summary["categories"]["scalability"]["risk"] in ["HIGH RISK", "CRITICAL RISK"]:
        actions.append(
            "Review partition strategy, consumer parallelism, and throughput capacity before production traffic."
        )

    if summary["categories"]["operational_safety"]["risk"] in [
        "HIGH RISK",
        "CRITICAL RISK",
    ]:
        actions.append(
            "Fix operational safety risks such as public access, IAM permissions, encryption, and governance tags."
        )

    if not actions:
        actions.append("Continue with standard production approval and monitoring.")

    return actions[:5]
