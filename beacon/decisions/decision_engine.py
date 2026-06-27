"""Core decision engine for production readiness determination.

This module implements the deterministic production decision logic.
It converts findings into actionable READY/NOT READY decisions.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum


class ProductionDecision(Enum):
    """Production readiness decision."""

    READY = "READY"
    NOT_READY = "NOT READY"


class RiskLevel(Enum):
    """Risk severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionEngine:
    """Engine for determining production readiness based on findings."""

    # Decision thresholds
    CRITICAL_THRESHOLD = 0  # Any critical finding = NOT READY
    HIGH_THRESHOLD = 2  # More than 2 high = consider NOT READY
    SCORE_THRESHOLD = 50  # Score below 50 = NOT READY

    OPERATIONAL_DECISION_TEMPLATES = [
        {
            "match": {
                "scanner.path.missing",
                "scanner.file.parse_failed",
                "engine.rule.execution_failed",
            },
            "action": "Fix Beacon input or collector errors, then rerun the readiness check",
            "target": "analysis",
            "safety": "SAFE",
            "decision_type": "analysis_blocker",
            "priority": 120,
            "why": "Beacon cannot make a reliable production-readiness decision while analysis inputs are missing or invalid.",
            "evidence_required": [
                "valid scan paths",
                "parseable input files",
                "successful collector execution",
            ],
            "do_not_do": [
                "Do not use a blocked analysis as a production release gate.",
            ],
        },
        {
            "match": {
                "cloud.database.rds.publicly_accessible",
                "cloud.database.azure.public_network_access.enabled",
                "cloud.database.gcp.public_ip.enabled",
                "cloud.key_vault.azure.public_network_access.enabled",
                "cloud.network.security_group.open_ingress",
                "cloud.network.gcp.firewall.open_ingress",
                "object_storage.public_access.enabled",
                "iac_coverage.resource.public_unmanaged",
            },
            "action": "Remove public exposure before approving production release",
            "target": "security",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 110,
            "why": "Public exposure on databases, storage, key vaults, or unmanaged infrastructure creates immediate security and blast-radius risk.",
            "evidence_required": [
                "private network path or approved ingress policy",
                "owner approval for any exception",
                "verification after network change",
            ],
            "do_not_do": [
                "Do not accept public exposure because the environment is non-production without an explicit owner-approved exception.",
                "Do not delete unmanaged public resources until ownership and blast radius are reviewed.",
            ],
        },
        {
            "match": {
                "flow.runtime.downstream_db_bottleneck",
                "database.runtime.latency.high",
                "database.runtime.connection_pool.exhaustion",
            },
            "action": "Investigate downstream database latency before scaling Kafka or API capacity",
            "target": "database",
            "safety": "SAFE",
            "decision_type": "incident_action",
            "priority": 105,
            "why": "Flow evidence points to downstream database pressure as the likely bottleneck.",
            "evidence_required": [
                "database p95/p99 latency",
                "connection pool saturation",
                "slow query or lock evidence",
                "consumer lag trend",
            ],
            "do_not_do": [
                "Do not scale Kafka first when downstream database evidence is stronger.",
                "Do not increase retries before checking database saturation.",
            ],
        },
        {
            "match": {
                "flow.runtime.deployment_correlated_degradation",
                "deployment.runtime.degradation_correlated",
                "deployment.window.kafka_lag_regression",
                "deployment.window.api_latency_regression",
                "deployment.window.error_rate_regression",
            },
            "action": "Pause rollout and evaluate rollback before scaling infrastructure",
            "target": "deployment",
            "safety": "CAUTION",
            "decision_type": "incident_action",
            "priority": 100,
            "why": "Degradation correlates with a deployment window, so rollback may be safer than broad scaling.",
            "evidence_required": [
                "deployment timestamp",
                "metric regression start time",
                "error, latency, or lag trend",
                "rollback safety check",
            ],
            "do_not_do": [
                "Do not scale everything blindly before checking whether the release introduced the regression.",
            ],
        },
        {
            "match_prefix": (
                "kafka.topic.replication_factor.",
                "kafka.topic.min_insync_replicas.",
                "kafka.cluster.broker_count.low",
                "kafka.cluster.under_replicated_partitions",
                "kafka.cluster.offline_partitions",
            ),
            "action": "Fix Kafka durability and broker-failure survivability before release",
            "target": "kafka",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 95,
            "why": "Kafka durability findings can lead to unavailable topics, data loss, or weak recovery during broker failure.",
            "evidence_required": [
                "broker count",
                "replication factor",
                "min.insync.replicas",
                "under-replicated/offline partition count",
            ],
            "do_not_do": [
                "Do not treat per-topic RF=1 findings as separate root causes when the cluster itself has only one broker.",
            ],
        },
        {
            "match_prefix": (
                "kafka.topic.retention",
                "kafka.topic.max_message_bytes",
                "kafka.runtime.disk_usage",
                "kafka.runtime.disk_growth",
                "kafka.runtime.message_size",
            ),
            "action": "Fix retention and payload growth drivers before adding broker storage",
            "target": "kafka_storage",
            "safety": "SAFE",
            "decision_type": "capacity_action",
            "priority": 90,
            "why": "Storage pressure is often caused by retention, payload growth, or lag rather than broker count alone.",
            "evidence_required": [
                "retention.ms and retention.bytes",
                "message size trend",
                "producer rate trend",
                "disk usage trend",
            ],
            "do_not_do": [
                "Do not expand brokers as the only fix if retention or payload size is the growth driver.",
            ],
        },
        {
            "match_prefix": (
                "k8s.workload.probes.",
                "k8s.workload.resources.",
                "k8s.workload.pod_disruption_budget.",
                "k8s.namespace.pod_security.",
                "k8s.admission_webhook.",
            ),
            "action": "Fix Kubernetes workload and admission safety before rollout",
            "target": "kubernetes",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 85,
            "why": "Kubernetes workload and admission-control gaps can turn deployment, node, or policy failures into user-facing incidents.",
            "evidence_required": [
                "workload probes",
                "resource requests/limits",
                "PodDisruptionBudget",
                "Pod Security admission labels",
                "webhook failurePolicy",
            ],
            "do_not_do": [
                "Do not rely on dashboards alone when admission or workload safety controls are missing.",
            ],
        },
        {
            "match": {
                "cloud.quota.headroom.insufficient",
                "cloud.compute.autoscaling.capacity.insufficient",
            },
            "action": "Create capacity and quota headroom before peak traffic or rollout",
            "target": "capacity",
            "safety": "SAFE",
            "decision_type": "capacity_action",
            "priority": 80,
            "why": "Capacity and quota gaps can block deployment, autoscaling, or incident recovery.",
            "evidence_required": [
                "current quota",
                "required capacity",
                "reserved buffer",
                "autoscaling min/desired/max",
            ],
            "do_not_do": [
                "Do not approve peak-load readiness while requested capacity plus buffer exceeds quota.",
            ],
        },
        {
            "match_prefix": ("iac_coverage.resource.",),
            "action": "Classify unmanaged cloud resources before import, deletion, or production approval",
            "target": "iac_coverage",
            "safety": "CAUTION",
            "decision_type": "governance_action",
            "priority": 75,
            "why": "Resources outside Terraform state can hide ownership, cost, dependency, security, and recovery risk.",
            "evidence_required": [
                "Terraform state match",
                "owner metadata",
                "cost/activity signal",
                "network exposure",
                "dependency/blast-radius review",
            ],
            "do_not_do": [
                "Do not blindly delete unmanaged resources with activity or unknown dependencies.",
            ],
        },
        {
            "match_prefix": (
                "schema_registry.compatibility.",
                "kafka.topic.schema_compatibility.",
            ),
            "action": "Set safe schema compatibility before producer release",
            "target": "schema_registry",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 70,
            "why": "Unsafe schema compatibility can break existing consumers during producer deployment.",
            "evidence_required": [
                "global compatibility",
                "subject compatibility",
                "producer schema change",
                "consumer compatibility expectation",
            ],
            "do_not_do": [
                "Do not release producer schema changes with compatibility NONE unless explicitly approved.",
            ],
        },
    ]

    @staticmethod
    def determine_production_decision(
        findings: List[Dict], score: int
    ) -> Tuple[ProductionDecision, str]:
        """Determine if system is production ready.

        Args:
            findings: List of finding dicts with 'severity' field
            score: Production readiness score (0-100)

        Returns:
            Tuple of (ProductionDecision, reasoning)
        """
        # Count findings by severity
        critical_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in findings if f.get("severity") == "HIGH")

        reasoning_parts = []

        # Rule 1: Any critical finding = NOT READY
        if critical_count > 0:
            reasoning_parts.append(
                f"System has {critical_count} critical finding(s) that must be resolved before production."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # Rule 2: Too many high-severity findings = NOT READY
        if high_count > DecisionEngine.HIGH_THRESHOLD:
            reasoning_parts.append(
                f"System has {high_count} high-severity findings. "
                f"More than {DecisionEngine.HIGH_THRESHOLD} high findings indicates operational risk."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # Rule 3: Low score = NOT READY
        if score < DecisionEngine.SCORE_THRESHOLD:
            reasoning_parts.append(
                f"Production readiness score ({score}/100) is below minimum threshold ({DecisionEngine.SCORE_THRESHOLD})."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # All checks passed
        reasoning_parts.append(
            f"System is production ready. "
            f"Score: {score}/100, Critical: {critical_count}, High: {high_count}."
        )
        return ProductionDecision.READY, " ".join(reasoning_parts)

    @staticmethod
    def categorize_findings(findings: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize findings by severity and risk area.

        Returns:
            Dict mapping severity level to list of findings
        """
        categorized = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
            "ERROR": [],
        }

        for finding in findings:
            severity = finding.get("severity", "MEDIUM")
            if severity in categorized:
                categorized[severity].append(finding)

        return categorized

    @staticmethod
    def identify_primary_risk_areas(findings: List[Dict]) -> List[Dict]:
        """Identify primary risk areas from findings.

        Returns:
            List of risk area summaries, ordered by criticality
        """
        risk_areas = {}

        for finding in findings:
            # Extract risk category from title or rule_id
            rule_id = finding.get("rule_id", "")
            title = finding.get("title", "")
            severity = finding.get("severity", "MEDIUM")

            # Infer risk area from rule_id (e.g., "kafka.topic.replication_factor.low" -> "Kafka Configuration")
            if rule_id.startswith("kafka"):
                risk_area = "Kafka Configuration"
            elif rule_id.startswith("aws.s3"):
                risk_area = "Object Storage Access Control"
            elif rule_id.startswith("iam"):
                risk_area = "IAM Permissions"
            else:
                risk_area = title.split(":")[0] if ":" in title else "General Risk"

            if risk_area not in risk_areas:
                risk_areas[risk_area] = {
                    "area": risk_area,
                    "count": 0,
                    "max_severity": severity,
                    "findings": [],
                }

            risk_areas[risk_area]["count"] += 1
            risk_areas[risk_area]["findings"].append(finding)

            # Update max severity
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            if severity_order.get(severity, 99) < severity_order.get(
                risk_areas[risk_area]["max_severity"], 99
            ):
                risk_areas[risk_area]["max_severity"] = severity

        # Sort by severity and count
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_areas = sorted(
            risk_areas.values(),
            key=lambda x: (severity_order.get(x["max_severity"], 99), -x["count"]),
        )

        return sorted_areas

    @staticmethod
    def prioritize_remediation_actions(findings: List[Dict], max_actions: int = 5) -> List[Dict]:
        """Prioritize remediation actions based on impact and severity.

        Returns:
            List of prioritized action recommendations
        """
        actions = []

        # Score each finding
        severity_scores = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}

        for finding in findings:
            severity = finding.get("severity", "MEDIUM")
            score = severity_scores.get(severity, 50)

            action = {
                "priority_score": score,
                "severity": severity,
                "title": finding.get("title", "Unknown issue"),
                "recommendation": finding.get("recommendation", "Review and remediate"),
                "impact": finding.get("impact", "Operational risk"),
                "evidence": finding.get("evidence"),
            }
            actions.append(action)

        # Sort by priority score (highest first)
        actions.sort(key=lambda x: x["priority_score"], reverse=True)

        # Return top N actions
        return actions[:max_actions]

    @staticmethod
    def build_operational_decisions(
        findings: List[Dict],
        summary: Optional[Dict] = None,
        max_decisions: int = 5,
    ) -> List[Dict]:
        """Build first-class ranked operational decisions.

        These are not raw finding recommendations. They are deterministic
        operational choices with safety, target, evidence, and anti-actions.
        """
        decisions = []
        seen = set()
        severity_scores = {
            "ERROR": 130,
            "CRITICAL": 120,
            "HIGH": 90,
            "MEDIUM": 55,
            "LOW": 20,
            "INFO": 0,
        }

        for finding in findings:
            template = DecisionEngine.match_decision_template(finding)
            if not template:
                continue

            key = (template["action"], template["target"])
            if key in seen:
                continue
            seen.add(key)

            severity = finding.get("severity", "INFO")
            priority_score = template["priority"] + severity_scores.get(severity, 0)
            decisions.append(
                {
                    "rank": 0,
                    "priority_score": priority_score,
                    "action": template["action"],
                    "target": template["target"],
                    "safety": template["safety"],
                    "decision_type": template["decision_type"],
                    "severity": severity,
                    "confidence": DecisionEngine.decision_confidence(
                        finding, template, summary or {}
                    ),
                    "why": template["why"],
                    "evidence": DecisionEngine.decision_evidence(finding),
                    "evidence_required": template["evidence_required"],
                    "do_not_do": template["do_not_do"],
                    "source_rule_ids": [finding.get("rule_id")],
                    "source_titles": [finding.get("title")],
                }
            )

        if not decisions and summary and summary.get("production_decision") == "READY":
            decisions.append(
                {
                    "rank": 1,
                    "priority_score": 0,
                    "action": "Proceed with standard release approval and monitoring",
                    "target": "release",
                    "safety": "SAFE",
                    "decision_type": "release_action",
                    "severity": "INFO",
                    "confidence": "MEDIUM",
                    "why": "Beacon did not find material production-readiness blockers in the analyzed inputs.",
                    "evidence": {},
                    "evidence_required": ["normal release approval", "monitoring coverage"],
                    "do_not_do": ["Do not skip normal change-management and rollback checks."],
                    "source_rule_ids": [],
                    "source_titles": [],
                }
            )

        decisions.sort(
            key=lambda item: (
                -item["priority_score"],
                item["target"],
                item["action"],
            )
        )
        for index, decision in enumerate(decisions[:max_decisions], 1):
            decision["rank"] = index

        return decisions[:max_decisions]

    @staticmethod
    def match_decision_template(finding: Dict) -> Dict | None:
        rule_id = finding.get("rule_id", "")

        for template in DecisionEngine.OPERATIONAL_DECISION_TEMPLATES:
            if rule_id in template.get("match", set()):
                return template
            if any(rule_id.startswith(prefix) for prefix in template.get("match_prefix", ())):
                return template

        return None

    @staticmethod
    def decision_confidence(finding: Dict, template: Dict, summary: Dict) -> str:
        severity = finding.get("severity")

        if template["decision_type"] == "analysis_blocker":
            return "HIGH"
        if severity in {"ERROR", "CRITICAL"}:
            return "HIGH"
        if summary.get("root_cause_hypotheses") and template["target"] in {
            "database",
            "deployment",
            "kafka_storage",
        }:
            return "HIGH"
        if severity == "HIGH":
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def decision_evidence(finding: Dict) -> Dict:
        return {
            "rule_id": finding.get("rule_id"),
            "title": finding.get("title"),
            "severity": finding.get("severity"),
            "category": finding.get("category"),
            "file": finding.get("file"),
            "evidence": finding.get("evidence") or {},
        }
