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
                "api.runtime.deployment_correlated_degradation",
                "kafka.history.deployment_correlated_lag",
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
            "match": {
                "deployment.window.kafka_lag_regression",
                "deployment.window.api_latency_regression",
                "deployment.window.error_rate_regression",
                "api.runtime.deployment_correlated_degradation",
                "kafka.history.deployment_correlated_lag",
            },
            "action": "Choose rollback investigation before capacity scaling for the changed service",
            "target": "rollback_decision",
            "safety": "CAUTION",
            "decision_type": "incident_action",
            "priority": 101,
            "why": "Before/after evidence points to a regression after deployment, so rollback evaluation is a safer first decision than infrastructure scaling.",
            "evidence_required": [
                "changed service and version",
                "deployment timestamp",
                "before/after metric deltas",
                "blast radius of rollback",
                "known feature flags or config changes",
            ],
            "do_not_do": [
                "Do not mask a release regression by scaling infrastructure first.",
                "Do not continue rollout while the changed service is still correlated with worsening signals.",
            ],
        },
        {
            "match": {
                "flow.runtime.cascading_latency",
                "api.runtime.latency_p95.high",
            },
            "action": "Reduce retry and timeout amplification before adding capacity",
            "target": "flow",
            "safety": "CAUTION",
            "decision_type": "incident_action",
            "priority": 98,
            "why": "Cascading latency can amplify API timeouts, retries, Kafka lag, and downstream saturation.",
            "evidence_required": [
                "API timeout and error trend",
                "retry rate",
                "consumer lag trend",
                "downstream latency",
                "queue or broker pressure",
            ],
            "do_not_do": [
                "Do not increase retries or timeouts without checking downstream capacity.",
                "Do not scale only the API tier if lag and downstream latency are already rising.",
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
            "match": {
                "kafka.consumer_group.hot_partition",
                "kafka.consumer_group.decision.partition_skew",
            },
            "action": "Fix producer partition-key skew before scaling consumers",
            "target": "kafka_partitioning",
            "safety": "SAFE",
            "decision_type": "incident_action",
            "priority": 94,
            "why": "Hot partitions limit consumer parallelism and can keep lag concentrated even after adding consumers.",
            "evidence_required": [
                "partition-level lag distribution",
                "producer partition key strategy",
                "message key cardinality",
                "consumer assignment",
            ],
            "do_not_do": [
                "Do not assume more consumers will fix lag when one partition is overloaded.",
                "Do not repartition a topic without validating ordering and replay impact.",
            ],
        },
        {
            "match": {
                "kafka.runtime.rebalance_storm",
                "kafka.consumer_group.rebalancing",
                "kafka.consumer_group.member_churn.high",
                "kafka.history.rebalance_churn.high",
                "kafka.history.consumer_group.member_churn",
                "kafka.runtime.consumer_group.unstable",
            },
            "action": "Stabilize consumer group membership before scaling or redeploying consumers",
            "target": "kafka_consumers",
            "safety": "SAFE",
            "decision_type": "incident_action",
            "priority": 93,
            "why": "Rebalance storms and member churn can pause consumption and amplify lag during incidents.",
            "evidence_required": [
                "consumer group state",
                "member churn history",
                "heartbeat and session timeout config",
                "max.poll.interval.ms",
                "recent deployment events",
            ],
            "do_not_do": [
                "Do not keep rolling consumer deployments while the group is already rebalancing.",
                "Do not add consumers until membership stability and partition assignment are understood.",
            ],
        },
        {
            "match": {
                "kafka.runtime.producer_throttle.high",
                "kafka.runtime.fetch_throttle.high",
                "kafka.runtime.producer_error_rate.high",
            },
            "action": "Identify throttled or noisy Kafka clients before expanding broker capacity",
            "target": "kafka_client_pressure",
            "safety": "SAFE",
            "decision_type": "capacity_action",
            "priority": 91,
            "why": "Producer/fetch throttling or producer error rate points to client pressure, quota behavior, or request saturation that broker expansion alone may not fix.",
            "evidence_required": [
                "top producers and consumers by throughput",
                "producer/fetch throttle time",
                "producer error classes",
                "client quota configuration",
                "request queue and network saturation",
            ],
            "do_not_do": [
                "Do not remove quotas during an incident without identifying the noisy client.",
                "Do not expand brokers before checking whether client behavior or quotas are the pressure source.",
            ],
        },
        {
            "match": {
                "kafka.topic.retention_ms.unbounded",
                "kafka.topic.retention_bytes.missing",
                "kafka.runtime.retention_bytes.missing_under_pressure",
                "kafka.runtime.message_size.increased_under_pressure",
            },
            "action": "Fix retention and payload policy before buying more Kafka storage",
            "target": "kafka_retention_cleanup",
            "safety": "SAFE",
            "decision_type": "capacity_action",
            "priority": 91,
            "why": "Retention gaps and payload growth create repeatable storage pressure; adding storage without fixing policy only delays the next saturation event.",
            "evidence_required": [
                "topic retention.ms and retention.bytes",
                "payload-size trend",
                "topic growth by producer",
                "replay and compliance retention requirement",
                "broker disk time-to-full",
            ],
            "do_not_do": [
                "Do not treat storage expansion as the long-term fix for unbounded retention.",
                "Do not lower retention below replay or compliance requirements just to clear disk pressure.",
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
            "match": {
                "kafka.runtime.replay.time_exceeds_target",
                "kafka.runtime.replay.no_drain_capacity",
                "kafka.runtime.replay.retention_window_insufficient",
            },
            "action": "Increase safe drain capacity or extend retention before backlog replay",
            "target": "kafka_replay",
            "safety": "CAUTION",
            "decision_type": "recovery_action",
            "priority": 88,
            "why": "Replay risk means the system may not drain backlog before retention expires or recovery targets are missed.",
            "evidence_required": [
                "backlog size",
                "consumer drain rate",
                "retention window",
                "replay SLO",
                "downstream capacity",
            ],
            "do_not_do": [
                "Do not start aggressive replay without validating downstream capacity.",
                "Do not shorten retention while backlog replay time exceeds the recovery target.",
            ],
        },
        {
            "match": {
                "kafka.runtime.producer_throttle.high",
                "kafka.runtime.fetch_throttle.high",
                "kafka.runtime.client_quotas.missing",
                "kafka.broker.client_quotas.missing",
                "kafka.runtime.request_queue_saturation.high",
                "kafka.runtime.network_saturation.high",
                "kafka.runtime.producer_error_rate.high",
            },
            "action": "Protect broker capacity with quotas and request-pressure investigation",
            "target": "kafka_capacity",
            "safety": "SAFE",
            "decision_type": "capacity_action",
            "priority": 86,
            "why": "Throttling, queue saturation, network pressure, and missing quotas can make one workload degrade the shared Kafka platform.",
            "evidence_required": [
                "producer and consumer quota config",
                "request queue time",
                "network throughput",
                "producer error rate",
                "top clients by throughput",
            ],
            "do_not_do": [
                "Do not remove throttles during an incident without identifying the noisy client.",
                "Do not scale brokers before checking whether quotas or client behavior are the pressure source.",
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
                "k8s.rbac.cluster_admin.broad_binding",
                "k8s.rbac.role.wildcard_permissions",
                "k8s.secret.inline_material",
                "k8s.workload.network_policy.missing",
                "k8s.container.privileged",
                "k8s.container.allow_privilege_escalation.enabled",
                "k8s.workload.host_namespace.enabled",
            },
            "action": "Remove Kubernetes privilege, secret, and network-isolation risks before rollout",
            "target": "kubernetes_security",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 108,
            "why": "Kubernetes privilege, secret-management, and network-isolation gaps can expand blast radius even when the workload appears healthy.",
            "evidence_required": [
                "least-privilege RBAC",
                "secret-manager or encrypted-secret workflow",
                "NetworkPolicy coverage",
                "container security context",
                "owner-approved exception if any control is intentionally absent",
            ],
            "do_not_do": [
                "Do not approve production rollout with broad cluster-admin access or inline secrets as an undocumented exception.",
                "Do not treat workload health as proof that cluster security posture is safe.",
            ],
        },
        {
            "match": {
                "k8s.runtime.deployment.unavailable",
                "k8s.runtime.pod.crash_loop",
                "k8s.runtime.pod.pending",
                "k8s.runtime.node.not_ready",
                "k8s.runtime.node.pressure",
                "readiness.correlation.kubernetes_single_point_of_failure",
            },
            "action": "Restore Kubernetes workload health before changing upstream traffic or Kafka capacity",
            "target": "kubernetes_runtime",
            "safety": "SAFE",
            "decision_type": "incident_action",
            "priority": 84,
            "why": "Unavailable pods, node pressure, or single-point-of-failure Kubernetes posture can be the immediate service degradation source.",
            "evidence_required": [
                "deployment availability",
                "pod events",
                "node pressure conditions",
                "recent rollout status",
                "readiness probe failures",
            ],
            "do_not_do": [
                "Do not scale Kafka first when consumer pods are unavailable or crash looping.",
                "Do not route more traffic to workloads with failing readiness or node pressure.",
            ],
        },
        {
            "match": {
                "cloud.quota.headroom.insufficient",
                "cloud.compute.autoscaling.capacity.insufficient",
                "readiness.correlation.capacity_plan_mismatch",
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
            "match": {
                "cloud.database.rds.backup_retention_missing",
                "cloud.database.rds.deletion_protection.disabled",
                "cloud.database.rds.multi_az.disabled",
                "cloud.database.rds.storage_encryption.disabled",
                "cloud.database.azure.backup_retention.weak",
                "cloud.database.azure.ha.disabled",
                "cloud.database.gcp.backup.disabled",
                "cloud.database.gcp.deletion_protection.disabled",
                "cloud.database.gcp.ha.disabled",
            },
            "action": "Fix managed database recovery, HA, and encryption posture before production approval",
            "target": "database_recovery",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 92,
            "why": "Managed database backup, deletion protection, HA, and encryption gaps weaken recovery from deletion, corruption, AZ failure, or data exposure.",
            "evidence_required": [
                "backup retention policy",
                "restore test or runbook",
                "deletion protection",
                "HA or approved non-prod exception",
                "encryption configuration",
            ],
            "do_not_do": [
                "Do not rely on snapshots or provider defaults without an explicit restore and ownership path.",
                "Do not waive database recovery gaps in production without a documented RPO/RTO exception.",
            ],
        },
        {
            "match": {
                "cicd.deployment.environment.missing",
                "cicd.deployment.concurrency.missing",
                "cicd.deployment.timeout.missing",
                "readiness.correlation.uncontrolled_production_deploy",
            },
            "action": "Add deployment guardrails before using the pipeline as a production release path",
            "target": "cicd",
            "safety": "SAFE",
            "decision_type": "release_blocker",
            "priority": 78,
            "why": "Weak deployment governance allows overlapping, unreviewed, or uncontrolled production changes.",
            "evidence_required": [
                "protected environment",
                "required reviewers or approval path",
                "deployment concurrency control",
                "deployment timeout",
                "rollback procedure",
            ],
            "do_not_do": [
                "Do not treat a pipeline as production-ready until concurrency and environment protection are explicit.",
                "Do not rely on manual coordination to prevent overlapping production deploys.",
            ],
        },
        {
            "match": {
                "iac_coverage.resource.active_unmanaged",
                "iac_coverage.resource.sensitive_unmanaged",
                "iac_coverage.resource.owner_missing",
            },
            "action": "Review ownership, activity, and blast radius before importing or deleting unmanaged resources",
            "target": "iac_coverage",
            "safety": "CAUTION",
            "decision_type": "governance_action",
            "priority": 82,
            "why": "Active, sensitive, or unowned unmanaged infrastructure may serve real traffic or hold data even when it is outside Terraform state.",
            "evidence_required": [
                "owner or service mapping",
                "recent activity or cost signal",
                "dependency review",
                "data sensitivity",
                "recommended disposition",
            ],
            "do_not_do": [
                "Do not import unmanaged resources before confirming ownership and desired lifecycle.",
                "Do not delete active or sensitive resources just because they are outside Terraform state.",
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
        {
            "match": {
                "kafka.consumer_group.lag.low",
                "kafka.consumer_group.decision.no_urgent_action",
                "kafka.runtime.decision.monitor_capacity",
            },
            "action": "Monitor the trend without urgent scaling or topology changes",
            "target": "monitoring",
            "safety": "SAFE",
            "decision_type": "monitor",
            "priority": 20,
            "why": "Current evidence does not show urgent degradation; the safest action is to watch trend and improve context.",
            "evidence_required": [
                "lag trend",
                "producer rate",
                "consumer throughput",
                "broker/storage trend",
            ],
            "do_not_do": [
                "Do not turn low or stable lag into emergency scaling.",
                "Do not make topology changes without trend evidence.",
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
                    "decision_label": DecisionEngine.decision_label(template["target"]),
                    "action": template["action"],
                    "target": template["target"],
                    "safety": template["safety"],
                    "decision_type": template["decision_type"],
                    "disposition": DecisionEngine.decision_disposition(finding, template),
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

        for decision in DecisionEngine.flow_ranking_decisions(summary or {}):
            key = (decision["action"], decision["target"])
            if key in seen:
                continue
            seen.add(key)
            decisions.append(decision)

        if not decisions and summary and summary.get("production_decision") == "READY":
            decisions.append(
                {
                    "rank": 1,
                    "priority_score": 0,
                    "decision_label": "Release Approval",
                    "action": "Proceed with standard release approval and monitoring",
                    "target": "release",
                    "safety": "SAFE",
                    "decision_type": "release_action",
                    "disposition": "proceed_with_standard_controls",
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
    def flow_ranking_decisions(summary: Dict) -> List[Dict]:
        """Create operational decisions from ranked flow bottleneck evidence."""
        decisions = []
        for ranking in (summary.get("flow_bottleneck_rankings") or [])[:3]:
            top_node = DecisionEngine.top_flow_path_node(ranking)
            if not top_node:
                continue
            source_findings = top_node.get("source_findings") or []
            target = DecisionEngine.flow_decision_target(top_node)
            decisions.append(
                {
                    "rank": 0,
                    "priority_score": DecisionEngine.flow_decision_priority(ranking, top_node),
                    "decision_label": DecisionEngine.decision_label(target),
                    "action": DecisionEngine.flow_decision_action(ranking, top_node),
                    "target": target,
                    "safety": DecisionEngine.flow_decision_safety(target),
                    "decision_type": "incident_action",
                    "disposition": "investigate_before_action",
                    "severity": DecisionEngine.highest_source_severity(source_findings),
                    "confidence": ranking.get("top_confidence") or top_node.get("confidence"),
                    "why": DecisionEngine.flow_decision_why(ranking, top_node),
                    "evidence": {
                        "flow": ranking.get("flow"),
                        "top_bottleneck": ranking.get("top_bottleneck"),
                        "incident_priority": ranking.get("incident_priority"),
                        "owner": ranking.get("owner"),
                        "criticality": ranking.get("criticality"),
                        "business_impact": ranking.get("business_impact"),
                        "node": {
                            "component": top_node.get("component"),
                            "component_type": top_node.get("component_type"),
                            "status": top_node.get("status"),
                            "confidence": top_node.get("confidence"),
                        },
                    },
                    "evidence_required": top_node.get("evidence_missing") or [],
                    "do_not_do": DecisionEngine.flow_decision_do_not_do(target),
                    "source_rule_ids": [
                        source.get("rule_id") for source in source_findings if source.get("rule_id")
                    ],
                    "source_titles": [
                        source.get("title") for source in source_findings if source.get("title")
                    ],
                    "source_findings": source_findings,
                }
            )
        return decisions

    @staticmethod
    def top_flow_path_node(ranking: Dict) -> Optional[Dict]:
        nodes = ranking.get("flow_path") or []
        for node in nodes:
            if node.get("is_bottleneck"):
                return node
        return nodes[0] if nodes else None

    @staticmethod
    def flow_decision_target(node: Dict) -> str:
        component_type = str(node.get("component_type") or node.get("component") or "").lower()
        if component_type in {"database", "storage", "deployment", "api"}:
            return component_type
        if component_type in {"consumer", "kafka", "producer"}:
            return f"kafka_{component_type}"
        return "flow"

    @staticmethod
    def flow_decision_priority(ranking: Dict, node: Dict) -> int:
        priority = 87
        if ranking.get("incident_priority") == "P1":
            priority += 28
        elif ranking.get("incident_priority") == "P2":
            priority += 18
        if (ranking.get("top_confidence") or node.get("confidence")) == "HIGH":
            priority += 15
        if str(ranking.get("criticality") or "").lower() in {"critical", "tier-0", "tier0"}:
            priority += 10
        return priority

    @staticmethod
    def flow_decision_action(ranking: Dict, node: Dict) -> str:
        target = DecisionEngine.flow_decision_target(node)
        flow = ranking.get("flow") or "the affected flow"
        actions = {
            "database": f"Inspect database pool, slow queries, locks, and I/O before scaling upstream services for {flow}",
            "api": f"Reduce API timeout and retry amplification before adding capacity for {flow}",
            "deployment": f"Pause rollout and evaluate rollback before scaling infrastructure for {flow}",
            "storage": f"Create storage headroom only after identifying the growth or I/O driver for {flow}",
            "kafka_consumer": f"Inspect consumer processing latency, group stability, and downstream calls before scaling Kafka for {flow}",
            "kafka_kafka": f"Inspect Kafka broker pressure, partition health, and producer behavior before changing consumers for {flow}",
            "kafka_producer": f"Inspect producer rate, payload size, partitioning, and throttling before scaling downstream consumers for {flow}",
        }
        return actions.get(
            target,
            f"Investigate the ranked bottleneck before broad scaling or rollback for {flow}",
        )

    @staticmethod
    def flow_decision_safety(target: str) -> str:
        if target in {"deployment", "storage"}:
            return "CAUTION"
        return "SAFE"

    @staticmethod
    def flow_decision_why(ranking: Dict, node: Dict) -> str:
        label = node.get("label") or node.get("component") or "a component"
        flow = ranking.get("flow") or "this flow"
        confidence = ranking.get("top_confidence") or node.get("confidence") or "UNKNOWN"
        impact = ranking.get("business_impact")
        why = (
            f"Beacon ranked {label} as the likely bottleneck for {flow} with "
            f"{confidence} confidence using flow-path evidence."
        )
        if impact:
            why += f" Business impact: {impact}"
        return why

    @staticmethod
    def flow_decision_do_not_do(target: str) -> List[str]:
        common = [
            "Do not scale every tier blindly before validating the ranked bottleneck.",
            "Do not ignore missing evidence; collect it before making risky changes.",
        ]
        by_target = {
            "database": [
                "Do not scale Kafka first when database pressure is the stronger signal.",
                "Do not increase retries before validating database saturation.",
            ],
            "api": [
                "Do not increase retry counts or timeouts while downstream latency is rising.",
                "Do not scale only the API tier if queueing and downstream pressure are already visible.",
            ],
            "deployment": [
                "Do not keep rolling forward until the deployment regression is ruled out.",
                "Do not mask a bad deploy with broad infrastructure scaling first.",
            ],
            "storage": [
                "Do not add storage as the only fix without finding the growth driver.",
                "Do not shorten retention while consumers still need replay headroom.",
            ],
            "kafka_consumer": [
                "Do not add consumers until processing latency and rebalance stability are understood.",
                "Do not blame brokers before checking consumer and downstream latency.",
            ],
            "kafka_kafka": [
                "Do not change consumer topology before checking broker pressure and partition health.",
                "Do not remove throttles without identifying the noisy client.",
            ],
            "kafka_producer": [
                "Do not scale consumers before checking producer partitioning and payload growth.",
                "Do not ignore producer error or throttle evidence.",
            ],
        }
        return by_target.get(target, common)

    @staticmethod
    def highest_source_severity(source_findings: List[Dict]) -> str:
        order = {"ERROR": 0, "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "INFO": 5}
        severities = [
            source.get("severity") for source in source_findings if source.get("severity") in order
        ]
        if not severities:
            return "INFO"
        return sorted(severities, key=lambda severity: order[severity])[0]

    @staticmethod
    def match_decision_template(finding: Dict) -> Optional[Dict]:
        rule_id = finding.get("rule_id", "")
        matches = []

        for template in DecisionEngine.OPERATIONAL_DECISION_TEMPLATES:
            if rule_id in template.get("match", set()):
                matches.append(template)
            if any(rule_id.startswith(prefix) for prefix in template.get("match_prefix", ())):
                matches.append(template)

        if not matches:
            return None
        return max(matches, key=lambda template: template.get("priority", 0))

    @staticmethod
    def decision_label(target: str) -> str:
        labels = {
            "analysis": "Analysis Blocked",
            "capacity": "Capacity Headroom",
            "cicd": "Deployment Guardrails",
            "database": "Downstream Database Bottleneck",
            "database_recovery": "Database Recovery Readiness",
            "deployment": "Deployment Regression",
            "flow": "Retry Cascade",
            "iac_coverage": "Unmanaged Resource Governance",
            "kafka": "Kafka Survivability",
            "kafka_capacity": "Kafka Capacity Protection",
            "kafka_client_pressure": "Kafka Client Pressure",
            "kafka_consumer": "Kafka Consumer Bottleneck",
            "kafka_consumers": "Kafka Consumer Stability",
            "kafka_kafka": "Kafka Broker Pressure",
            "kafka_partitioning": "Hot Partition / Key Skew",
            "kafka_producer": "Kafka Producer Pressure",
            "kafka_replay": "Kafka Replay Readiness",
            "kafka_retention_cleanup": "Retention Cleanup",
            "kafka_storage": "Kafka Storage Pressure",
            "kubernetes": "Kubernetes Workload Safety",
            "kubernetes_runtime": "Kubernetes Runtime Health",
            "kubernetes_security": "Kubernetes Security Posture",
            "monitoring": "Monitor Only",
            "rollback_decision": "Rollback vs Scale",
            "schema_registry": "Schema Compatibility",
            "security": "Public Exposure Blocker",
            "storage": "Storage Capacity Pressure",
        }
        return labels.get(
            target,
            str(target or "Operational Decision").replace("_", " ").title(),
        )

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
    def decision_disposition(finding: Dict, template: Dict) -> str:
        decision_type = template.get("decision_type")
        severity = finding.get("severity")

        if decision_type == "analysis_blocker":
            return "rerun_after_fix"
        if decision_type == "release_blocker":
            return "fix_before_rollout"
        if decision_type in {"incident_action", "capacity_action", "recovery_action"}:
            return "investigate_before_action"
        if decision_type == "governance_action":
            return "review_before_change"
        if decision_type == "monitor":
            return "monitor"
        if severity in {"ERROR", "CRITICAL", "HIGH"}:
            return "fix_before_rollout"
        return "monitor"

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
