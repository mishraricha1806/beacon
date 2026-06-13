from beacon.readiness.interpretation import SEVERITY_ORDER


CORRELATION_DEFINITIONS = [
    {
        "rule_id": "readiness.correlation.internet_exposed_database",
        "required": {
            "cloud.network.security_group.open_ingress",
            "cloud.database.rds.publicly_accessible",
        },
        "severity": "CRITICAL",
        "title": "Internet-exposed database path detected",
        "impact": "Public ingress controls combined with a publicly accessible database create a direct data-plane exposure path.",
        "recommendation": "Move the database to private subnets, remove direct public ingress, and require approved private access paths before production rollout.",
        "tags": ["readiness", "correlation", "cloud", "database"],
    },
    {
        "rule_id": "readiness.correlation.storage_data_exposure",
        "required": {
            "object_storage.public_access.enabled",
            "object_storage.encryption.missing",
        },
        "severity": "CRITICAL",
        "title": "Public unencrypted object storage exposure detected",
        "impact": "Public access plus missing encryption significantly increases the likelihood and impact of sensitive data disclosure.",
        "recommendation": "Block public access, enable encryption, and validate least-privilege access before promotion.",
        "tags": ["readiness", "correlation", "storage", "security"],
    },
    {
        "rule_id": "readiness.correlation.uncontrolled_production_deploy",
        "required": {
            "cicd.deployment.environment.missing",
        },
        "any_of": {
            "cicd.github.permissions.write_all",
            "cicd.github.third_party_actions.unpinned",
        },
        "severity": "CRITICAL",
        "title": "Production deployment workflow lacks governance and supply-chain safeguards",
        "impact": "A deployment path without protected environments combined with broad token permissions or unpinned actions increases the chance of unsafe or tampered releases.",
        "recommendation": "Require protected environments, least-privilege permissions, and SHA-pinned third-party actions for deployment workflows.",
        "tags": ["readiness", "correlation", "cicd", "supply-chain"],
    },
    {
        "rule_id": "readiness.correlation.kubernetes_single_point_of_failure",
        "required": {
            "k8s.workload.replicas.single",
        },
        "any_of": {
            "topology.service.critical_single_instance",
            "k8s.workload.host_namespace.enabled",
            "k8s.workload.topology_spread.missing",
        },
        "severity": "HIGH",
        "title": "Kubernetes workload has compounding single-point-of-failure risk",
        "impact": "Single replica deployment posture combined with topology or isolation weaknesses increases outage likelihood during routine disruptions.",
        "recommendation": "Run multiple replicas, add topology protection, and remove unnecessary host namespace sharing before production rollout.",
        "tags": ["readiness", "correlation", "kubernetes", "availability"],
    },
    {
        "rule_id": "readiness.correlation.capacity_plan_mismatch",
        "required": {
            "cloud.quota.headroom.insufficient",
            "cloud.compute.autoscaling.capacity.insufficient",
        },
        "severity": "CRITICAL",
        "title": "Cloud capacity plan cannot satisfy declared scaling policy",
        "impact": "Quota exhaustion combined with no autoscaling headroom can block rollout and leave production without burst capacity.",
        "recommendation": "Increase quota headroom and autoscaling limits together so capacity policy and platform limits stay aligned.",
        "tags": ["readiness", "correlation", "cloud", "capacity"],
    },
]


def correlation_finding(rule_id, severity, title, impact, recommendation, evidence, tags):
    return {
        "rule_id": rule_id,
        "domain": "readiness",
        "category": "operational_safety",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": evidence.get("files", ["readiness-correlation"])[0],
        "evidence": evidence,
        "tags": tags,
    }


def finding_sort_key(finding):
    return SEVERITY_ORDER.get(finding.get("severity", "INFO"), 99), finding.get("rule_id", "")


def augment_readiness_findings(findings):
    findings = list(findings or [])
    rule_ids = {finding.get("rule_id") for finding in findings}
    existing_keys = {
        (
            finding.get("rule_id"),
            tuple(sorted((finding.get("evidence") or {}).get("files", []))),
        )
        for finding in findings
    }

    for definition in CORRELATION_DEFINITIONS:
        required = definition.get("required", set())
        any_of = definition.get("any_of")
        if not required <= rule_ids:
            continue
        if any_of and not (set(any_of) & rule_ids):
            continue

        matched = [
            finding
            for finding in findings
            if finding.get("rule_id") in required or finding.get("rule_id") in (any_of or set())
        ]
        matched.sort(key=finding_sort_key)
        files = sorted({finding.get("file") for finding in matched if finding.get("file")})
        key = (definition["rule_id"], tuple(files))
        if key in existing_keys:
            continue

        findings.append(
            correlation_finding(
                rule_id=definition["rule_id"],
                severity=definition["severity"],
                title=definition["title"],
                impact=definition["impact"],
                recommendation=definition["recommendation"],
                evidence={
                    "matched_rule_ids": [finding.get("rule_id") for finding in matched],
                    "files": files,
                },
                tags=definition["tags"],
            )
        )
        existing_keys.add(key)

    return findings
