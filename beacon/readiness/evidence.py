import hashlib
import json

from beacon.contracts import RELEASE_EVIDENCE_SCHEMA_VERSION, contract_metadata

BLOCKING_SEVERITIES = {"ERROR", "CRITICAL"}
MAJOR_SEVERITIES = {"HIGH"}


def build_release_evidence_pack(summary, findings):
    interpreted = summary.get("interpreted_findings") or findings or []
    grouped_risks = summary.get("grouped_risks") or []
    blocking_risks = risk_rows(grouped_risks, interpreted, BLOCKING_SEVERITIES)
    major_risks = risk_rows(grouped_risks, interpreted, MAJOR_SEVERITIES)
    waived_risks = waived_rows(interpreted)

    evidence = {
        **contract_metadata(RELEASE_EVIDENCE_SCHEMA_VERSION),
        "decision": summary.get("production_decision"),
        "score": summary.get("score"),
        "score_status": summary.get("score_status"),
        "environment": summary.get("environment"),
        "survivability": summary.get("survivability"),
        "primary_risk_area": summary.get("primary_risk_area"),
        "domains_covered": domains_covered(interpreted),
        "evidence_files": evidence_files(interpreted),
        "evidence_quality": evidence_quality(interpreted),
        "counts": {
            "critical": summary.get("critical", 0),
            "high": summary.get("high", 0),
            "medium": summary.get("medium", 0),
            "low": summary.get("low", 0),
            "info": summary.get("info", 0),
            "error": summary.get("error", 0),
            "raw_critical": summary.get("raw_critical", 0),
            "raw_high": summary.get("raw_high", 0),
            "suppressed_duplicate_findings": summary.get("suppressed_duplicate_count", 0),
            "waived_findings": waived_count(interpreted),
        },
        "blocking_risks": blocking_risks,
        "major_risks": major_risks,
        "waived_risks": waived_risks,
        "top_reasons": summary.get("top_reasons", [])[:5],
        "next_best_actions": summary.get("next_best_actions", [])[:5],
        "fix_plan": summary.get("fix_plan", [])[:8],
        "release_review_checklist": summary.get("release_review_checklist", []),
        "coverage": coverage(summary),
        "service_governance": (summary.get("environment_readiness") or {}).get("service_governance")
        or {},
    }
    evidence["production_blockers"] = build_production_blockers(summary, evidence)
    return evidence


def build_production_blockers(summary, evidence):
    release_gate = summary.get("release_gate") or {}
    blocking_risks = evidence.get("blocking_risks") or []
    major_risks = evidence.get("major_risks") or []

    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR":
        status = "Analysis blocked"
        blockers = [
            {
                "severity": "ERROR",
                "title": reason.replace("ERROR: ", "", 1),
                "affected_count": 1,
                "recommendation": "Resolve Beacon analysis errors and rerun the readiness check.",
            }
            for reason in summary.get("top_reasons", [])[:5]
        ]
    elif blocking_risks:
        status = "Production is blocked"
        blockers = blocking_risks
    elif major_risks:
        status = "Major risks before release"
        blockers = major_risks
    else:
        status = "No production blockers found"
        blockers = []

    return {
        "question": "What blocks production?",
        "status": status,
        "decision": summary.get("production_decision"),
        "score": summary.get("score"),
        "environment": summary.get("environment"),
        "blockers": blockers[:5],
        "fix_first": (release_gate.get("fix_first") or summary.get("next_best_actions") or [])[:5],
        "business_impact": release_gate.get("business_risk") or summary.get("business_summary"),
    }


def domains_covered(findings):
    domains = {finding.get("domain") for finding in findings if finding.get("domain")}
    return sorted(domains)


def evidence_files(findings):
    files = {finding.get("file") for finding in findings if finding.get("file")}
    return sorted(files)


def evidence_quality(findings):
    freshness = {"CURRENT": 0, "STALE": 0, "UNKNOWN": 0}
    confidence = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    evidence_bound = 0
    for finding in findings:
        assessment = (finding.get("evidence") or {}).get("assessment") or {}
        freshness_value = assessment.get("freshness", "UNKNOWN")
        confidence_value = assessment.get("confidence", "LOW")
        freshness[freshness_value] = freshness.get(freshness_value, 0) + 1
        confidence[confidence_value] = confidence.get(confidence_value, 0) + 1
        if assessment.get("evidence_bound") is True:
            evidence_bound += 1
    return {
        "freshness": freshness,
        "confidence": confidence,
        "evidence_bound_findings": evidence_bound,
        "total_findings": len(findings),
    }


def waived_count(findings):
    return sum(1 for finding in findings if finding.get("waived") is True)


def risk_rows(grouped_risks, findings, severities):
    rows = []
    grouped_titles = set()
    for risk in grouped_risks:
        if risk.get("severity") not in severities:
            continue
        grouped_titles.add(risk.get("title"))
        rows.append(
            {
                "fingerprint": risk_fingerprint(risk),
                "severity": risk.get("severity"),
                "title": risk.get("title"),
                "category": risk.get("business_category") or risk.get("category"),
                "affected_count": risk.get("affected_count", 0),
                "recommendation": risk.get("recommendation"),
                "remediation_command": risk.get("remediation_command"),
                "examples": risk.get("examples", [])[:5],
            }
        )

    for finding in findings:
        if finding.get("severity") not in severities:
            continue
        if finding.get("title") in grouped_titles:
            continue
        rows.append(
            {
                "fingerprint": risk_fingerprint(finding),
                "severity": finding.get("severity"),
                "title": finding.get("title"),
                "category": finding.get("business_category") or finding.get("category"),
                "affected_count": 1,
                "recommendation": finding.get("recommendation"),
                "remediation_command": finding.get("remediation_command"),
                "examples": [finding.get("file")] if finding.get("file") else [],
            }
        )
    return rows[:10]


def risk_fingerprint(risk):
    """Return a stable group identity without exposing raw evidence values."""
    identity = {
        "key": risk.get("key"),
        "rule_id": risk.get("rule_id"),
        "title": risk.get("title") if not risk.get("key") else None,
        "category": risk.get("business_category") or risk.get("category"),
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def waived_rows(findings):
    rows = []
    for finding in findings:
        if finding.get("waived") is not True:
            continue
        rows.append(
            {
                "rule_id": finding.get("rule_id"),
                "title": finding.get("title"),
                "original_severity": finding.get("policy_original_severity")
                or finding.get("original_severity"),
                "current_severity": finding.get("severity"),
                "reason": finding.get("waiver_reason"),
                "expires": finding.get("waiver_expires"),
                "file": finding.get("file"),
            }
        )
    return rows[:20]


def coverage(summary):
    distributed = summary.get("distributed_system_readiness") or {}
    environment = summary.get("environment_readiness") or {}
    return {
        "domains_observed": distributed.get("domains_observed", []),
        "critical_paths": distributed.get("critical_paths", [])[:5],
        "environment_model_confidence": environment.get("confidence"),
        "coverage_gaps": environment.get("coverage_gaps", [])[:5],
    }
