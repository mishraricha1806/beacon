from collections import defaultdict

from beacon.scoring import count_severities

SEVERITY_ORDER = {
    "ERROR": 6,
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


SYSTEM_DIMENSIONS = [
    {
        "key": "application_runtime",
        "title": "Application/API Readiness",
        "domains": {"api", "service"},
        "purpose": "Can user-facing services handle latency, errors, retries, and rollout pressure?",
    },
    {
        "key": "event_streaming",
        "title": "Event Streaming Readiness",
        "domains": {"kafka", "schema_registry"},
        "purpose": "Can event pipelines survive broker, schema, lag, replay, and partition pressure?",
    },
    {
        "key": "compute_orchestration",
        "title": "Compute/Kubernetes Readiness",
        "domains": {"kubernetes", "k8s"},
        "purpose": "Can workloads stay schedulable, healthy, probed, resourced, and fault tolerant?",
    },
    {
        "key": "data_layer",
        "title": "Database/Storage Readiness",
        "domains": {"database", "storage", "object_storage"},
        "purpose": "Can data stores handle capacity, backups, retention, latency, and recovery?",
    },
    {
        "key": "security_access",
        "title": "Security/IAM Readiness",
        "domains": {"iam", "cloud", "security"},
        "purpose": "Are access, public exposure, encryption, and least-privilege controls production safe?",
    },
    {
        "key": "delivery_change",
        "title": "Deployment/CI-CD Readiness",
        "domains": {"cicd", "deployment"},
        "purpose": "Can changes roll out safely without unsafe permissions, missing environment context, or correlated degradation?",
    },
    {
        "key": "flow_correlation",
        "title": "Flow/Topology Readiness",
        "domains": {"flow", "topology", "opentelemetry", "prometheus"},
        "purpose": "Can Beacon reason across services, Kafka, databases, deployments, and telemetry?",
    },
]


def build_distributed_system_readiness(findings, summary):
    findings = findings or []
    domains = sorted({normalize_domain(finding.get("domain")) for finding in findings})
    domains = [domain for domain in domains if domain]
    dimensions = [dimension_status(dimension, findings) for dimension in SYSTEM_DIMENSIONS]
    observed_dimensions = [item for item in dimensions if item["observed"]]
    release_blockers = distributed_release_blockers(findings)

    return {
        "title": "Distributed System Production Readiness",
        "verdict": distributed_verdict(summary, release_blockers, observed_dimensions),
        "confidence": distributed_confidence(summary, observed_dimensions),
        "scope": "whole distributed system",
        "domains_observed": domains,
        "observed_dimension_count": len(observed_dimensions),
        "dimension_count": len(SYSTEM_DIMENSIONS),
        "dimensions": dimensions,
        "release_blockers": release_blockers,
        "coverage_gaps": distributed_coverage_gaps(dimensions),
        "critical_paths": infer_critical_paths(domains),
    }


def build_environment_readiness_model(environment_model, distributed_readiness):
    environment_model = environment_model or {}
    distributed_readiness = distributed_readiness or {}
    dimensions = distributed_readiness.get("dimensions") or []
    observed = [dimension for dimension in dimensions if dimension.get("observed")]
    blocked = [
        dimension for dimension in observed if dimension.get("status") in {"BLOCKED", "HIGH_RISK"}
    ]

    service_count = environment_model.get("service_count", 0)
    dependency_domains = environment_model.get("dependency_domains") or []
    business_flows = environment_model.get("business_flows") or []

    if not environment_model:
        verdict = "No explicit environment model was provided."
        confidence = "LOW"
    elif blocked:
        verdict = "Environment is not ready; one or more observed readiness domains are blocked or high risk."
        confidence = environment_model_confidence(environment_model, observed)
    elif observed:
        verdict = "Environment model was evaluated with no observed blocked readiness domains."
        confidence = environment_model_confidence(environment_model, observed)
    else:
        verdict = "Environment model loaded, but no readiness domains were observed."
        confidence = "LOW"

    return {
        "name": environment_model.get("name") or "unknown",
        "profile": environment_model.get("profile"),
        "criticality": environment_model.get("criticality"),
        "owner": environment_model.get("owner"),
        "rto": environment_model.get("rto"),
        "rpo": environment_model.get("rpo"),
        "business_flows": business_flows,
        "service_count": service_count,
        "dependency_domains": dependency_domains,
        "observed_dimension_count": len(observed),
        "dimension_count": len(dimensions),
        "blocked_dimensions": [
            {
                "title": dimension.get("title"),
                "status": dimension.get("status"),
                "max_severity": dimension.get("max_severity"),
                "finding_count": dimension.get("finding_count"),
            }
            for dimension in blocked
        ],
        "verdict": verdict,
        "confidence": confidence,
        "coverage_gaps": environment_coverage_gaps(environment_model, distributed_readiness),
    }


def environment_model_confidence(environment_model, observed_dimensions):
    score = 0
    if environment_model.get("services"):
        score += 1
    if environment_model.get("dependencies"):
        score += 1
    if environment_model.get("business_flows"):
        score += 1
    if environment_model.get("rto") or environment_model.get("rpo"):
        score += 1
    if len(observed_dimensions) >= 5:
        score += 2
    elif len(observed_dimensions) >= 3:
        score += 1

    if score >= 5:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def environment_coverage_gaps(environment_model, distributed_readiness):
    gaps = []
    if not environment_model.get("services"):
        gaps.append("Add services to the environment model.")
    if not environment_model.get("dependencies"):
        gaps.append("Add dependency domains such as Kafka, Kubernetes, database, and storage.")
    if not environment_model.get("business_flows"):
        gaps.append("Add business flows so Beacon can map technical risk to user impact.")
    if not environment_model.get("rto") and not environment_model.get("rpo"):
        gaps.append("Add RTO/RPO targets for recovery readiness.")

    gaps.extend(distributed_readiness.get("coverage_gaps") or [])
    return gaps[:6]


def dimension_status(dimension, findings):
    matching = [
        finding
        for finding in findings
        if normalize_domain(finding.get("domain")) in dimension["domains"]
    ]
    counts = count_severities(matching)
    max_severity = max_severity_for(matching)
    status = dimension_readiness_status(max_severity)

    return {
        "key": dimension["key"],
        "title": dimension["title"],
        "purpose": dimension["purpose"],
        "domains": sorted(dimension["domains"]),
        "observed": bool(matching),
        "status": status,
        "max_severity": max_severity,
        "finding_count": len(matching),
        "critical": counts["critical"],
        "high": counts["high"],
        "medium": counts["medium"],
        "top_findings": top_dimension_findings(matching),
    }


def distributed_verdict(summary, release_blockers, observed_dimensions):
    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR":
        return "Analysis blocked; fix collector or parsing errors before using Beacon as a release gate."
    if not observed_dimensions:
        return "No distributed-system inputs were observed."
    if release_blockers:
        return "Not release-ready across the distributed system; fix the highest-risk cross-domain blockers first."
    if summary.get("high", 0) > 0:
        return "Release has material distributed-system risks that need review before approval."
    if summary.get("medium", 0) > 0:
        return "Release is possible with documented distributed-system risks and follow-up actions."
    return "No material distributed-system production blockers were found in the analyzed inputs."


def distributed_confidence(summary, observed_dimensions):
    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR":
        return "LOW"
    if len(observed_dimensions) >= 5:
        return "HIGH"
    if len(observed_dimensions) >= 3:
        return "MEDIUM"
    return "LOW"


def distributed_release_blockers(findings):
    blockers = [
        finding for finding in findings if finding.get("severity") in {"ERROR", "CRITICAL", "HIGH"}
    ]
    return [
        {
            "severity": finding.get("severity"),
            "domain": normalize_domain(finding.get("domain")) or "unknown",
            "title": finding.get("title"),
            "recommendation": finding.get("recommendation"),
            "rule_id": finding.get("rule_id"),
        }
        for finding in sorted(blockers, key=finding_sort_key)[:8]
    ]


def distributed_coverage_gaps(dimensions):
    gaps = []
    for dimension in dimensions:
        if not dimension["observed"]:
            gaps.append(
                f"{dimension['title']} was not analyzed; add inputs for {', '.join(dimension['domains'])}."
            )
    return gaps[:5]


def infer_critical_paths(domains):
    paths = []
    domain_set = set(domains)

    if {"api", "kafka", "database"}.issubset(domain_set) or {
        "flow",
        "kafka",
        "database",
    }.issubset(domain_set):
        paths.append("API -> Kafka -> Consumer -> Database")

    if {"deployment", "api"}.issubset(domain_set) or {"deployment", "flow"}.issubset(domain_set):
        paths.append("Deployment -> API/runtime degradation")

    if {"kubernetes", "api"}.issubset(domain_set):
        paths.append("Kubernetes workload -> API availability")

    if {"kafka", "schema_registry"}.issubset(domain_set):
        paths.append("Producer schema change -> Kafka topic -> consumer compatibility")

    if {"cloud", "iam"}.issubset(domain_set) or {"cloud", "storage"}.issubset(domain_set):
        paths.append("Cloud access/storage -> production blast radius")

    return paths or ["No complete cross-domain critical path was inferred yet."]


def top_dimension_findings(findings):
    return [
        {
            "severity": finding.get("severity"),
            "title": finding.get("title"),
            "rule_id": finding.get("rule_id"),
        }
        for finding in sorted(findings, key=finding_sort_key)[:3]
    ]


def max_severity_for(findings):
    if not findings:
        return "NOT_OBSERVED"
    return max(
        (finding.get("severity", "INFO") for finding in findings),
        key=lambda severity: SEVERITY_ORDER.get(severity, 0),
    )


def dimension_readiness_status(max_severity):
    if max_severity in {"ERROR", "CRITICAL"}:
        return "BLOCKED"
    if max_severity == "HIGH":
        return "HIGH_RISK"
    if max_severity == "MEDIUM":
        return "REVIEW"
    if max_severity in {"LOW", "INFO"}:
        return "OBSERVED"
    return "NOT_OBSERVED"


def finding_sort_key(finding):
    return (
        -SEVERITY_ORDER.get(finding.get("severity", "INFO"), 0),
        str(finding.get("domain") or ""),
        str(finding.get("title") or ""),
    )


def normalize_domain(domain):
    if not domain:
        return None
    normalized = str(domain).lower().replace("-", "_")
    aliases = {
        "k8s": "kubernetes",
        "schema": "schema_registry",
        "schema_registry": "schema_registry",
        "object_storage": "storage",
        "s3": "storage",
        "gcs": "storage",
        "terraform": "cloud",
    }
    return aliases.get(normalized, normalized)
