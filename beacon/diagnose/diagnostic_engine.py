from collections import Counter, defaultdict

from beacon.correlations.root_cause import correlate_findings
from beacon.diagnose.flow_ranker import build_flow_bottleneck_rankings
from beacon.readiness.interpretation import SEVERITY_ORDER, sort_findings


MATERIAL_SEVERITIES = {"ERROR", "CRITICAL", "HIGH", "MEDIUM"}


DIAGNOSTIC_USE_CASES = [
    {
        "id": "module2.kafka.consumer_lag",
        "title": "Why is Kafka consumer lag increasing?",
        "module": "Module 2",
        "goal": "Distinguish Kafka capacity problems from consumer-side or downstream bottlenecks.",
        "rule_ids": {
            "kafka.consumer_group.lag.high",
            "kafka.consumer_group.lag.moderate",
            "kafka.consumer_group.lag.low",
            "kafka.consumer_group.hot_partition",
            "kafka.runtime.consumer_lag.increasing_under_pressure",
            "kafka.history.consumer_lag.growing",
            "kafka.history.deployment_correlated_lag",
            "kafka.consumer_group.decision.consumer_side",
            "flow.runtime.downstream_db_bottleneck",
        },
        "correlation_ids": {
            "correlation.root_cause.downstream_database_bottleneck",
            "correlation.root_cause.kafka_consumer_observation",
        },
        "always_show_evidence_needed": True,
        "evidence_needed": [
            "producer rate trend",
            "consumer processing latency",
            "downstream database/API latency",
            "broker health and request latency",
        ],
    },
    {
        "id": "module2.kafka.scale_or_optimize",
        "title": "Should we scale Kafka or optimize consumers/configuration?",
        "module": "Module 2",
        "goal": "Avoid blind broker expansion when retention, payload, or consumer pressure is the real driver.",
        "rule_ids": {
            "kafka.runtime.disk_usage.critical",
            "kafka.runtime.disk_usage.high",
            "kafka.runtime.disk_growth.high",
            "kafka.runtime.retention_bytes.missing_under_pressure",
            "kafka.runtime.message_size.increased_under_pressure",
            "kafka.runtime.producer_rate.increased_under_pressure",
            "kafka.history.producer_rate.increased",
            "kafka.topic.retention_ms.unbounded",
            "kafka.topic.max_message_bytes.large",
            "kafka.runtime.decision.capacity_protection",
            "kafka.runtime.decision.retention_cleanup",
            "kafka.runtime.decision.disk_expansion",
        },
        "correlation_ids": {
            "correlation.root_cause.kafka_payload_storage_growth",
            "correlation.root_cause.storage_capacity_pressure",
        },
        "evidence_needed": [
            "broker disk by broker",
            "topic growth rate",
            "retention.ms and retention.bytes",
            "producer payload-size trend",
        ],
    },
    {
        "id": "module2.kafka.partition_skew",
        "title": "Why is one partition overloaded?",
        "module": "Module 2",
        "goal": "Detect skew before incorrectly scaling consumers.",
        "rule_ids": {
            "kafka.consumer_group.hot_partition",
            "kafka.consumer_group.decision.partition_skew",
            "kafka.runtime.replica_load.high",
            "kafka.runtime.leader_imbalance.high",
            "kafka.cluster.leader_imbalance.high",
        },
        "correlation_ids": set(),
        "evidence_needed": [
            "lag by partition",
            "producer partition key distribution",
            "leader distribution",
            "consumer concurrency",
        ],
    },
    {
        "id": "module2.kafka.consumer_instability",
        "title": "Why are consumers unstable?",
        "module": "Module 2",
        "goal": "Detect rebalances, dead members, and consumer-group churn.",
        "rule_ids": {
            "kafka.runtime.rebalance_storm",
            "kafka.runtime.consumer_group.unstable",
            "kafka.runtime.consumer_group.no_active_members",
            "kafka.runtime.consumer_group.member_shortfall",
            "kafka.consumer_group.rebalancing",
            "kafka.consumer_group.empty",
            "kafka.consumer_group.member_churn.high",
            "kafka.history.rebalance_churn.high",
            "kafka.history.consumer_group.member_churn",
            "kafka.consumer.heartbeat_session.mismatch",
        },
        "correlation_ids": set(),
        "evidence_needed": [
            "consumer group state over time",
            "member count trend",
            "deployment timeline",
            "heartbeat/session/poll interval configuration",
        ],
    },
    {
        "id": "module2.kafka.cluster_health",
        "title": "Is Kafka itself unhealthy or is the problem downstream?",
        "module": "Module 2",
        "goal": "Separate broker/control-plane health problems from consumer or downstream dependency issues.",
        "rule_ids": {
            "kafka.runtime.offline_partitions",
            "kafka.runtime.under_replicated_partitions",
            "kafka.runtime.under_min_isr_partitions",
            "kafka.runtime.controller_count.invalid",
            "kafka.runtime.controller_churn.high",
            "kafka.runtime.partition_reassignment.active",
            "kafka.runtime.replication_fetcher_lag.high",
            "kafka.runtime.request_latency.high",
            "kafka.runtime.request_queue_saturation.high",
            "kafka.runtime.network_saturation.high",
            "kafka.runtime.broker_disk_skew.critical",
            "kafka.runtime.broker_disk_skew.high",
            "kafka.cluster.offline_partitions",
            "kafka.cluster.under_replicated_partitions",
            "kafka.cluster.under_min_isr_partitions",
        },
        "correlation_ids": {"correlation.root_cause.kafka_single_broker_topology"},
        "evidence_needed": [
            "broker health by node",
            "controller election/churn history",
            "request queue and network saturation",
            "replication fetcher lag by broker",
        ],
    },
    {
        "id": "module2.kafka.replay_survivability",
        "title": "Can this system replay backlog before retention expires?",
        "module": "Module 2",
        "goal": "Estimate whether consumers can recover from backlog within replay and retention windows.",
        "rule_ids": {
            "kafka.runtime.replay.no_drain_capacity",
            "kafka.runtime.replay.time_exceeds_target",
            "kafka.runtime.replay.retention_window_insufficient",
            "kafka.consumer.auto_offset_reset.latest",
            "kafka.topic.retention_ms.low",
            "kafka.topic.retention_ms.unbounded",
            "kafka.topic.retention_bytes.missing",
        },
        "correlation_ids": {
            "correlation.root_cause.kafka_payload_storage_growth",
            "correlation.root_cause.kafka_consumer_observation",
        },
        "evidence_needed": [
            "current backlog by consumer group",
            "consumer drain rate",
            "retention remaining hours",
            "replay SLO target",
        ],
    },
    {
        "id": "module2.kafka.schema_poison_message",
        "title": "Could schema or poison messages break consumers?",
        "module": "Module 2",
        "goal": "Detect schema compatibility and DLQ gaps that can turn producer changes into consumer incidents.",
        "rule_ids": {
            "schema_registry.compatibility.global_unsafe",
            "schema_registry.subject.compatibility.unsafe",
            "schema_registry.topic.subject.missing",
            "schema_registry.subject.latest_schema.missing",
            "kafka.runtime.schema_registry.unavailable",
            "kafka.runtime.schema_incompatible_changes",
            "kafka.topic.schema_compatibility.unsafe",
            "kafka.consumer.dlq.missing",
        },
        "correlation_ids": {"correlation.root_cause.kafka_schema_governance"},
        "evidence_needed": [
            "subject-level compatibility",
            "producer deployment timeline",
            "consumer deserialization error rate",
            "DLQ/retry topic configuration",
        ],
    },
    {
        "id": "module2.kafka.auth_quota_throttling",
        "title": "Are clients failing because of auth, ACLs, quotas, or throttling?",
        "module": "Module 2",
        "goal": "Identify access-control or quota pressure before incorrectly scaling brokers or consumers.",
        "rule_ids": {
            "kafka.runtime.producer_throttle.high",
            "kafka.runtime.fetch_throttle.high",
            "kafka.runtime.producer_error_rate.high",
            "kafka.runtime.client_quotas.missing",
            "kafka.runtime.acl.none_found",
            "kafka.runtime.acl.broad_allow",
            "kafka.runtime.acl.analysis_unavailable",
            "kafka.acl.export.broad_allow",
            "kafka.broker.client_quotas.missing",
            "kafka.broker.security.allow_everyone_if_no_acl",
            "kafka.runtime.access.auth.plaintext",
        },
        "correlation_ids": set(),
        "evidence_needed": [
            "producer/fetch throttle time",
            "client quota configuration",
            "ACL bindings for affected principals",
            "producer/consumer auth error classes",
        ],
    },
    {
        "id": "module2.kubernetes.workload_instability",
        "title": "Is Kubernetes workload instability driving runtime degradation?",
        "module": "Module 2",
        "goal": "Find pod, node, and deployment health issues that can slow consumers or APIs.",
        "rule_ids": {
            "k8s.runtime.node.not_ready",
            "k8s.runtime.node.pressure",
            "k8s.runtime.pod.crash_loop",
            "k8s.runtime.pod.pending",
            "k8s.runtime.deployment.unavailable",
            "k8s.workload.probes.missing",
            "k8s.workload.replicas.single",
        },
        "correlation_ids": {"correlation.root_cause.kubernetes_workload_instability"},
        "evidence_needed": [
            "pod events",
            "node pressure details",
            "rollout status",
            "readiness/liveness probe behavior",
        ],
    },
    {
        "id": "module2.platform.capacity_pressure",
        "title": "Is platform capacity pressure causing degradation?",
        "module": "Module 2",
        "goal": "Connect database, storage, and Kafka capacity signals before choosing a scaling action.",
        "rule_ids": {
            "storage.runtime.capacity.high",
            "storage.runtime.growth_rate.high",
            "storage.runtime.iops_saturation.high",
            "database.runtime.storage_saturation",
            "database.runtime.latency.high",
            "database.runtime.connection_pool.exhaustion",
            "database.runtime.lock_contention.high",
            "database.runtime.replication_lag.high",
            "kafka.runtime.disk_usage.critical",
            "kafka.runtime.disk_usage.high",
            "kafka.runtime.disk_growth.high",
        },
        "correlation_ids": {
            "correlation.root_cause.storage_capacity_pressure",
            "correlation.root_cause.downstream_database_bottleneck",
        },
        "evidence_needed": [
            "capacity by storage/backend",
            "growth rate",
            "I/O saturation",
            "database latency and pool pressure",
        ],
    },
    {
        "id": "module3.flow.bottleneck",
        "title": "Where is the bottleneck across the flow?",
        "module": "Module 3",
        "goal": "Rank the most likely constrained component across API, Kafka, consumer, and database.",
        "rule_ids": {
            "flow.runtime.downstream_db_bottleneck",
            "flow.runtime.component_unhealthy",
            "database.runtime.latency.high",
            "database.runtime.connection_pool.exhaustion",
            "api.runtime.latency_p95.high",
        },
        "correlation_ids": {
            "correlation.root_cause.downstream_database_bottleneck",
            "correlation.root_cause.kubernetes_workload_instability",
        },
        "evidence_needed": [
            "flow topology",
            "API latency/error rate",
            "Kafka lag trend",
            "database latency and pool pressure",
        ],
    },
    {
        "id": "module3.flow.deployment_triggered",
        "title": "Did deployment trigger degradation?",
        "module": "Module 3",
        "goal": "Correlate runtime degradation with rollout/deployment signals.",
        "rule_ids": {
            "flow.runtime.deployment_correlated_degradation",
            "api.runtime.deployment_correlated_degradation",
            "deployment.runtime.degradation_correlated",
            "kafka.history.deployment_correlated_lag",
            "k8s.runtime.deployment.unavailable",
        },
        "correlation_ids": {"correlation.root_cause.deployment_regression"},
        "evidence_needed": [
            "deployment timestamp",
            "rollout status",
            "error/latency before and after deployment",
            "feature-flag changes",
        ],
    },
    {
        "id": "module3.flow.cascading_latency",
        "title": "Why is latency cascading across systems?",
        "module": "Module 3",
        "goal": "Detect timeout/retry amplification across dependent systems.",
        "rule_ids": {
            "flow.runtime.cascading_latency",
            "api.runtime.timeout_rate.high",
            "api.runtime.retry_amplification",
            "kafka.runtime.consumer_lag.increasing_under_pressure",
            "storage.runtime.capacity.high",
        },
        "correlation_ids": {
            "correlation.root_cause.retry_cascade",
            "correlation.root_cause.storage_capacity_pressure",
        },
        "evidence_needed": [
            "API timeout rate",
            "retry rate",
            "Kafka lag trend",
            "downstream dependency saturation",
        ],
    },
]


def build_diagnostic_summary(findings):
    sorted_items = sort_findings(findings)
    material = [
        finding
        for finding in sorted_items
        if finding.get("severity") in MATERIAL_SEVERITIES
    ]
    hypotheses = correlate_findings(sorted_items, limit=5)

    summary = {
        "diagnostic_status": diagnostic_status(sorted_items, hypotheses),
        "severity_counts": severity_counts(sorted_items),
        "primary_hypothesis": hypotheses[0] if hypotheses else None,
        "root_cause_hypotheses": hypotheses,
        "affected_domains": affected_domains(sorted_items),
        "material_findings": material[:10],
        "first_actions": first_actions(material, hypotheses),
        "evidence_summary": evidence_summary(material, hypotheses),
        "telemetry_gaps": telemetry_gaps(sorted_items, hypotheses),
        "diagnostic_playbooks": diagnostic_playbooks(sorted_items, hypotheses),
        "consumer_group_diagnoses": consumer_group_diagnoses(sorted_items, hypotheses),
        "flow_bottleneck_rankings": build_flow_bottleneck_rankings(sorted_items),
        "deployment_window_analyses": deployment_window_analyses(sorted_items),
        "scope": diagnostic_scope(sorted_items),
    }

    summary["incident_diagnosis"] = incident_diagnosis(summary)
    summary["executive_summary"] = executive_summary(summary)
    return summary


def incident_diagnosis(summary):
    primary = summary.get("primary_hypothesis")
    consumer_diagnoses = summary.get("consumer_group_diagnoses") or []
    playbooks = summary.get("diagnostic_playbooks") or []
    first_actions = summary.get("first_actions") or []
    telemetry_gaps = summary.get("telemetry_gaps") or []

    if consumer_diagnoses and should_prioritize_consumer_diagnosis(
        consumer_diagnoses[0], primary
    ):
        return incident_diagnosis_from_consumer_group(
            consumer_diagnoses[0], first_actions, telemetry_gaps
        )

    if playbooks and is_generic_kafka_observation(primary):
        return incident_diagnosis_from_playbook(
            playbooks[0], first_actions, telemetry_gaps
        )

    if primary:
        return {
            "title": primary.get("title"),
            "source": "root_cause_hypothesis",
            "confidence": primary.get("confidence", "MEDIUM"),
            "summary": primary.get("impact") or primary.get("title"),
            "recommendation": primary.get("recommendation"),
            "evidence": incident_evidence_from_hypothesis(primary, summary),
            "first_actions": first_actions[:4],
            "missing_evidence": telemetry_gaps[:4],
        }

    if consumer_diagnoses:
        return incident_diagnosis_from_consumer_group(
            consumer_diagnoses[0], first_actions, telemetry_gaps
        )

    if playbooks:
        return incident_diagnosis_from_playbook(
            playbooks[0], first_actions, telemetry_gaps
        )

    return {
        "title": "No major runtime degradation detected",
        "source": "diagnostic_status",
        "confidence": "LOW",
        "summary": summary.get("diagnostic_status"),
        "recommendation": first_non_empty(first_actions),
        "evidence": ["No material runtime incident pattern was matched."],
        "first_actions": first_actions[:4],
        "missing_evidence": telemetry_gaps[:4],
    }


def should_prioritize_consumer_diagnosis(diagnosis, primary):
    cause = diagnosis.get("primary_likely_cause")
    if cause in {
        "partition_skew_or_hot_key",
        "consumer_group_instability",
        "offsets_missing_or_group_inactive",
    }:
        return True
    if cause == "lag_requires_more_evidence":
        return primary is None
    return False


def is_generic_kafka_observation(primary):
    if not primary:
        return False
    return (
        primary.get("correlation_id")
        == "correlation.root_cause.kafka_consumer_observation"
    )


def incident_diagnosis_from_consumer_group(diagnosis, first_actions, telemetry_gaps):
    title = humanize_cause(diagnosis.get("primary_likely_cause"))
    return {
        "title": title,
        "source": "consumer_group_diagnosis",
        "confidence": diagnosis.get("confidence", "MEDIUM"),
        "summary": (
            f"Consumer group {diagnosis.get('consumer_group')} is "
            f"{diagnosis.get('status', 'observed').lower()}."
        ),
        "recommendation": first_non_empty(diagnosis.get("first_actions"))
        or first_non_empty(first_actions),
        "evidence": incident_evidence_from_consumer_group(diagnosis),
        "first_actions": (diagnosis.get("first_actions") or first_actions)[:4],
        "missing_evidence": (diagnosis.get("evidence_missing") or telemetry_gaps)[:4],
    }


def incident_diagnosis_from_playbook(playbook, first_actions, telemetry_gaps):
    return {
        "title": playbook.get("title"),
        "source": "diagnostic_playbook",
        "confidence": playbook.get("confidence", "MEDIUM"),
        "summary": playbook.get("goal"),
        "recommendation": first_scenario_action(first_actions),
        "evidence": [
            f"Matched rules: {', '.join(playbook.get('matched_rule_ids') or [])}"
        ],
        "first_actions": first_actions[:4],
        "missing_evidence": (playbook.get("evidence_needed") or telemetry_gaps)[:4],
    }


def incident_evidence_from_hypothesis(primary, summary):
    evidence = []
    matched = primary.get("matched_rule_ids") or []
    if matched:
        evidence.append("Matched rules: " + ", ".join(matched[:5]))

    domains = [
        f"{item['domain']} ({item['max_severity']})"
        for item in summary.get("affected_domains", [])[:4]
    ]
    if domains:
        evidence.append("Affected domains: " + ", ".join(domains))

    return evidence or [primary.get("title")]


def incident_evidence_from_consumer_group(diagnosis):
    evidence = [
        f"Consumer group: {diagnosis.get('consumer_group')}",
        f"Status: {diagnosis.get('status')}",
        f"Likely cause: {diagnosis.get('primary_likely_cause')}",
    ]
    if diagnosis.get("total_lag") is not None:
        evidence.append(f"Total lag: {diagnosis.get('total_lag')}")
    if diagnosis.get("max_partition_lag") is not None:
        evidence.append(f"Max partition lag: {diagnosis.get('max_partition_lag')}")
    if diagnosis.get("hot_partitions"):
        evidence.append(f"Hot partitions: {diagnosis.get('hot_partitions')}")
    return evidence


def humanize_cause(cause):
    if not cause:
        return "Runtime signal needs more evidence"
    return cause.replace("_", " ").title()


def first_non_empty(items):
    for item in items or []:
        if item:
            return item
    return None


def first_scenario_action(items):
    generic_prefixes = (
        "Check whether the consumer group is expected to be active",
        "Review the deployment diff",
        "Review large-payload topics",
    )
    for item in items or []:
        if item and not item.startswith(generic_prefixes):
            return item
    return first_non_empty(items)


def diagnostic_status(findings, hypotheses):
    if any(finding.get("severity") == "ERROR" for finding in findings):
        return "BLOCKED"
    if hypotheses:
        return "ROOT_CAUSE_CANDIDATES_FOUND"
    if any(finding.get("severity") in {"CRITICAL", "HIGH"} for finding in findings):
        return "DEGRADATION_SIGNALS_FOUND"
    if any(finding.get("severity") == "MEDIUM" for finding in findings):
        return "REVIEW_SIGNALS_FOUND"
    return "NO_MAJOR_RUNTIME_DEGRADATION_DETECTED"


def severity_counts(findings):
    counts = Counter(finding.get("severity", "INFO") for finding in findings)
    return {
        severity: counts.get(severity, 0)
        for severity in ("ERROR", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
    }


def affected_domains(findings):
    domains = defaultdict(lambda: {"findings": 0, "max_severity": "INFO"})

    for finding in findings:
        domain = finding.get("domain") or "unknown"
        severity = finding.get("severity", "INFO")
        domains[domain]["findings"] += 1
        if SEVERITY_ORDER.get(severity, 99) < SEVERITY_ORDER.get(
            domains[domain]["max_severity"], 99
        ):
            domains[domain]["max_severity"] = severity

    return [
        {"domain": domain, **data}
        for domain, data in sorted(
            domains.items(),
            key=lambda item: (
                SEVERITY_ORDER.get(item[1]["max_severity"], 99),
                -item[1]["findings"],
                item[0],
            ),
        )
    ]


def first_actions(material_findings, hypotheses):
    actions = []

    for hypothesis in hypotheses[:3]:
        action = hypothesis.get("recommendation")
        if action and action not in actions:
            actions.append(action)

    for finding in material_findings:
        action = finding.get("recommendation")
        if action and action not in actions:
            actions.append(action)

    return actions[:5] or [
        "Continue observing runtime signals and rerun diagnosis if degradation appears."
    ]


def evidence_summary(material_findings, hypotheses):
    evidence = []

    for hypothesis in hypotheses[:3]:
        evidence.append(
            {
                "type": "root_cause_hypothesis",
                "title": hypothesis["title"],
                "confidence": hypothesis["confidence"],
                "matched_rule_ids": hypothesis.get("matched_rule_ids", []),
            }
        )

    for finding in material_findings[:5]:
        evidence.append(
            {
                "type": "finding",
                "severity": finding.get("severity"),
                "title": finding.get("title"),
                "rule_id": finding.get("rule_id"),
                "evidence": finding.get("evidence", {}),
            }
        )

    return evidence


def telemetry_gaps(findings, hypotheses):
    rule_ids = {finding.get("rule_id") for finding in findings}
    domains = {finding.get("domain") for finding in findings}
    gaps = []

    if not hypotheses and any(
        finding.get("severity") in {"CRITICAL", "HIGH"} for finding in findings
    ):
        gaps.append(
            "High-severity runtime signals were found, but there is not enough cross-domain evidence to rank a root cause."
        )

    if "kafka.consumer_group.offsets.missing" in rule_ids:
        gaps.append(
            "Consumer group offset findings need activity context: expected group state, producer rate, and recent deployment history."
        )

    if "kafka.consumer_group.lag.high" in rule_ids and not {
        "database",
        "flow",
        "api",
    }.intersection(domains):
        gaps.append(
            "Kafka lag needs downstream application, database, or flow telemetry before Beacon can distinguish Kafka capacity from consumer-side bottlenecks."
        )

    if "schema_registry.compatibility.global_unsafe" in rule_ids:
        gaps.append(
            "Schema Registry findings need producer deployment timeline and subject-level compatibility to estimate consumer breakage risk."
        )

    if not gaps:
        gaps.append(
            "No major telemetry gaps detected for the current diagnostic scope."
        )

    return gaps[:5]


def diagnostic_playbooks(findings, hypotheses):
    rule_ids = {finding.get("rule_id") for finding in findings}
    correlation_ids = {hypothesis.get("correlation_id") for hypothesis in hypotheses}
    matched = []

    for use_case in DIAGNOSTIC_USE_CASES:
        matched_rules = sorted(rule_ids.intersection(use_case["rule_ids"]))
        matched_correlations = sorted(
            correlation_ids.intersection(use_case["correlation_ids"])
        )

        if not matched_rules:
            continue

        confidence = playbook_confidence(matched_rules, matched_correlations)
        matched.append(
            {
                "id": use_case["id"],
                "module": use_case["module"],
                "title": use_case["title"],
                "goal": use_case["goal"],
                "confidence": confidence,
                "matched_rule_ids": matched_rules,
                "matched_correlation_ids": matched_correlations,
                "evidence_needed": missing_playbook_evidence(
                    use_case, rule_ids, correlation_ids
                ),
            }
        )

    matched.sort(
        key=lambda item: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(item["confidence"], 3),
            item["module"],
            item["title"],
        )
    )
    return matched[:8]


def playbook_confidence(matched_rules, matched_correlations):
    if matched_correlations and len(matched_rules) >= 2:
        return "HIGH"
    if matched_correlations or len(matched_rules) >= 2:
        return "MEDIUM"
    return "LOW"


def missing_playbook_evidence(use_case, rule_ids, correlation_ids):
    if correlation_ids.intersection(use_case["correlation_ids"]) and not use_case.get(
        "always_show_evidence_needed"
    ):
        return []
    if len(rule_ids.intersection(use_case["rule_ids"])) >= 2:
        return use_case["evidence_needed"][:2]
    return use_case["evidence_needed"][:3]


def diagnostic_scope(findings):
    return {
        "finding_count": len(findings),
        "domains": sorted({finding.get("domain", "unknown") for finding in findings}),
        "rule_count": len({finding.get("rule_id") for finding in findings}),
    }


def deployment_window_analyses(findings):
    by_service = defaultdict(list)

    for finding in findings:
        if not str(finding.get("rule_id", "")).startswith("deployment.window."):
            continue
        evidence = finding.get("evidence") or {}
        service = evidence.get("service") or "unknown-service"
        by_service[service].append(finding)

    analyses = []
    for service, service_findings in sorted(by_service.items()):
        metrics = []
        deployed_at = None
        version = None
        namespace = None

        for finding in service_findings:
            evidence = finding.get("evidence") or {}
            deployed_at = deployed_at or evidence.get("deployed_at")
            version = version or evidence.get("version")
            namespace = namespace or evidence.get("namespace")
            metrics.append(
                {
                    "metric": evidence.get("metric"),
                    "before": evidence.get("before"),
                    "after": evidence.get("after"),
                    "delta": evidence.get("delta"),
                    "ratio": evidence.get("ratio"),
                    "severity": finding.get("severity"),
                    "rule_id": finding.get("rule_id"),
                    "title": finding.get("title"),
                }
            )

        analyses.append(
            {
                "service": service,
                "version": version,
                "namespace": namespace,
                "deployed_at": deployed_at,
                "metric_count": len(metrics),
                "metrics": sorted(metrics, key=lambda item: item["metric"] or ""),
            }
        )

    return analyses


def consumer_group_diagnoses(findings, hypotheses):
    groups = defaultdict(list)

    for finding in findings:
        group = consumer_group_from_finding(finding)
        if group:
            groups[group].append(finding)

    return [
        build_consumer_group_diagnosis(group, group_findings, findings, hypotheses)
        for group, group_findings in sorted(groups.items())
    ]


def consumer_group_from_finding(finding):
    evidence = finding.get("evidence") or {}
    group = evidence.get("consumer_group") or evidence.get("group_id")
    if group:
        return str(group)
    return None


def build_consumer_group_diagnosis(group, group_findings, all_findings, hypotheses):
    rule_ids = {finding.get("rule_id") for finding in group_findings}
    all_rule_ids = {finding.get("rule_id") for finding in all_findings}
    domains = {finding.get("domain") for finding in all_findings}
    lag_finding = first_matching(
        group_findings,
        {
            "kafka.consumer_group.lag.high",
            "kafka.consumer_group.lag.moderate",
            "kafka.consumer_group.lag.low",
        },
    )
    hot_partition_finding = first_matching(
        group_findings, {"kafka.consumer_group.hot_partition"}
    )
    state_finding = first_matching(
        group_findings,
        {
            "kafka.consumer_group.rebalancing",
            "kafka.consumer_group.empty",
            "kafka.runtime.consumer_group.unstable",
            "kafka.runtime.consumer_group.no_active_members",
            "kafka.runtime.consumer_group.member_shortfall",
        },
    )
    churn_finding = first_matching(
        group_findings,
        {
            "kafka.consumer_group.member_churn.high",
            "kafka.history.consumer_group.member_churn",
        },
    )

    lag_evidence = (lag_finding or {}).get("evidence") or {}
    hot_evidence = (hot_partition_finding or {}).get("evidence") or {}
    state_evidence = (state_finding or {}).get("evidence") or {}

    likely_cause = consumer_group_likely_cause(
        rule_ids, all_rule_ids, domains, hypotheses
    )
    evidence_missing = consumer_group_evidence_missing(rule_ids, all_rule_ids, domains)

    return {
        "consumer_group": group,
        "status": consumer_group_status(rule_ids, lag_evidence, state_evidence),
        "total_lag": lag_evidence.get("total_lag") or lag_evidence.get("lag"),
        "partition_count": lag_evidence.get("partition_count"),
        "max_partition_lag": lag_evidence.get("max_partition_lag")
        or hot_evidence.get("max_partition_lag"),
        "hot_partitions": hot_evidence.get("hot_partitions", []),
        "affected_topics": affected_topics_for_group(group_findings),
        "group_state": state_evidence.get("state"),
        "member_count": state_evidence.get("member_count"),
        "committed_offsets_status": committed_offsets_status(rule_ids),
        "primary_likely_cause": likely_cause["cause"],
        "confidence": likely_cause["confidence"],
        "evidence_used": consumer_group_evidence_used(group_findings, hypotheses),
        "evidence_missing": evidence_missing,
        "first_actions": consumer_group_first_actions(
            likely_cause["cause"], group_findings, evidence_missing
        ),
        "matched_rule_ids": sorted(rule_ids),
    }


def first_matching(findings, rule_ids):
    for finding in findings:
        if finding.get("rule_id") in rule_ids:
            return finding
    return None


def consumer_group_status(rule_ids, lag_evidence, state_evidence):
    if "kafka.consumer_group.offsets.missing" in rule_ids:
        return "OFFSETS_MISSING"
    if "kafka.consumer_group.rebalancing" in rule_ids:
        return "REBALANCING"
    if "kafka.consumer_group.empty" in rule_ids:
        return "EMPTY"
    if "kafka.consumer_group.lag.high" in rule_ids:
        return "HIGH_LAG"
    if "kafka.consumer_group.lag.moderate" in rule_ids:
        return "MODERATE_LAG"
    if "kafka.consumer_group.lag.low" in rule_ids:
        return "LOW_LAG"
    return state_evidence.get("state") or lag_evidence.get("status") or "OBSERVED"


def committed_offsets_status(rule_ids):
    if "kafka.consumer_group.offsets.missing" in rule_ids:
        return "MISSING"
    if any(rule_id.startswith("kafka.consumer_group.lag.") for rule_id in rule_ids):
        return "FOUND"
    return "UNKNOWN"


def consumer_group_likely_cause(rule_ids, all_rule_ids, domains, hypotheses):
    correlation_ids = {hypothesis.get("correlation_id") for hypothesis in hypotheses}

    if "kafka.consumer_group.offsets.missing" in rule_ids:
        return {
            "cause": "offsets_missing_or_group_inactive",
            "confidence": "MEDIUM",
        }

    if rule_ids.intersection(
        {
            "kafka.consumer_group.rebalancing",
            "kafka.consumer_group.empty",
            "kafka.consumer_group.member_churn.high",
            "kafka.history.consumer_group.member_churn",
            "kafka.runtime.consumer_group.unstable",
            "kafka.runtime.consumer_group.no_active_members",
            "kafka.runtime.consumer_group.member_shortfall",
        }
    ):
        return {"cause": "consumer_group_instability", "confidence": "HIGH"}

    if rule_ids.intersection(
        {
            "kafka.consumer_group.hot_partition",
            "kafka.consumer_group.decision.partition_skew",
        }
    ):
        return {"cause": "partition_skew_or_hot_key", "confidence": "HIGH"}

    if "kafka.consumer_group.decision.partition_parallelism" in rule_ids:
        return {"cause": "partition_parallelism_limit", "confidence": "HIGH"}

    if (
        "correlation.root_cause.downstream_database_bottleneck" in correlation_ids
        or "flow.runtime.downstream_db_bottleneck" in all_rule_ids
        or domains.intersection({"database", "flow", "api"})
        and "kafka.consumer_group.lag.high" in rule_ids
    ):
        return {
            "cause": "downstream_dependency_or_consumer_bottleneck",
            "confidence": "HIGH",
        }

    if "kafka.consumer_group.decision.consumer_side" in rule_ids:
        return {"cause": "consumer_side_processing_bottleneck", "confidence": "MEDIUM"}

    if "kafka.consumer_group.lag.high" in rule_ids:
        return {"cause": "lag_requires_more_evidence", "confidence": "MEDIUM"}

    if "kafka.consumer_group.lag.moderate" in rule_ids:
        return {"cause": "moderate_lag_monitor_trend", "confidence": "MEDIUM"}

    return {"cause": "no_urgent_consumer_lag_action", "confidence": "HIGH"}


def consumer_group_evidence_missing(rule_ids, all_rule_ids, domains):
    missing = []

    if "kafka.consumer_group.offsets.missing" in rule_ids:
        missing.extend(
            ["expected group activity", "producer rate", "deployment history"]
        )

    if any(rule_id.startswith("kafka.consumer_group.lag.") for rule_id in rule_ids):
        if not {"flow", "database", "api"}.intersection(domains):
            missing.append("downstream API/database latency")
        if not all_rule_ids.intersection(
            {
                "kafka.runtime.producer_rate.increased_under_pressure",
                "kafka.runtime.producer_error_rate.high",
            }
        ):
            missing.append("producer throughput/error trend")
        if not all_rule_ids.intersection(
            {
                "kafka.runtime.request_latency.high",
                "kafka.runtime.request_queue_saturation.high",
                "kafka.runtime.network_saturation.high",
                "kafka.runtime.under_replicated_partitions",
            }
        ):
            missing.append("broker request/network/replication health")

    if rule_ids.intersection(
        {
            "kafka.consumer_group.hot_partition",
            "kafka.consumer_group.decision.partition_skew",
        }
    ):
        missing.append("producer partition-key distribution")

    if rule_ids.intersection(
        {"kafka.consumer_group.rebalancing", "kafka.consumer_group.member_churn.high"}
    ):
        missing.append("deployment and member churn timeline")

    return dedupe(missing)[:6]


def consumer_group_evidence_used(findings, hypotheses):
    evidence = [
        {
            "rule_id": finding.get("rule_id"),
            "severity": finding.get("severity"),
            "title": finding.get("title"),
            "evidence": finding.get("evidence", {}),
        }
        for finding in findings[:6]
    ]

    for hypothesis in hypotheses[:3]:
        if any(
            rule_id in hypothesis.get("matched_rule_ids", [])
            for rule_id in {finding.get("rule_id") for finding in findings}
        ):
            evidence.append(
                {
                    "correlation_id": hypothesis.get("correlation_id"),
                    "confidence": hypothesis.get("confidence"),
                    "title": hypothesis.get("title"),
                }
            )

    return evidence[:8]


def consumer_group_first_actions(cause, findings, evidence_missing):
    actions_by_cause = {
        "offsets_missing_or_group_inactive": [
            "Confirm whether the consumer group is expected to be active and committing offsets.",
            "Check consumer deployment health before treating this as lag.",
        ],
        "consumer_group_instability": [
            "Inspect rolling deployments, consumer crashes, heartbeat/session timeout, and max.poll settings.",
            "Stabilize membership before scaling consumers.",
        ],
        "partition_skew_or_hot_key": [
            "Review producer partition key distribution and recent keying changes.",
            "Do not scale consumers blindly until hot partitions are understood.",
        ],
        "partition_parallelism_limit": [
            "Compare consumer concurrency with partition count and ordering requirements.",
            "Increase partitions only after validating keying and replay impact.",
        ],
        "downstream_dependency_or_consumer_bottleneck": [
            "Investigate downstream database/API latency and consumer processing time before scaling Kafka.",
            "Check retry amplification and poison-message behavior.",
        ],
        "consumer_side_processing_bottleneck": [
            "Check consumer processing time, thread pools, retries, DB/API calls, and recent deployments.",
            "Compare producer rate with consumer drain rate.",
        ],
        "lag_requires_more_evidence": [
            "Collect producer rate, broker health, and downstream dependency telemetry.",
            "Check lag by partition before choosing a scaling action.",
        ],
        "moderate_lag_monitor_trend": [
            "Monitor lag trend and compare against producer throughput.",
            "Investigate if lag continues to grow across the next time window.",
        ],
        "no_urgent_consumer_lag_action": [
            "Continue monitoring lag trend.",
            "Rerun diagnosis if lag grows or consumer group state changes.",
        ],
    }

    actions = list(actions_by_cause.get(cause, []))
    for finding in findings:
        recommendation = finding.get("recommendation")
        if recommendation and recommendation not in actions:
            actions.append(recommendation)

    if evidence_missing:
        actions.append(
            "Collect missing evidence: " + ", ".join(evidence_missing[:3]) + "."
        )

    return actions[:5]


def affected_topics_for_group(findings):
    topics = []
    for finding in findings:
        evidence = finding.get("evidence") or {}
        if evidence.get("topic"):
            topics.append(evidence["topic"])
        for partition in evidence.get("hot_partitions", []) or []:
            if partition.get("topic"):
                topics.append(partition["topic"])
    return dedupe(topics)


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def executive_summary(summary):
    primary = summary.get("primary_hypothesis")
    if summary["diagnostic_status"] == "BLOCKED":
        return (
            "Beacon could not complete diagnosis because one or more collectors failed."
        )

    if primary:
        return (
            f"Beacon found {primary['confidence']} confidence root-cause candidate: "
            f"{primary['title']}."
        )

    if summary["material_findings"]:
        top = summary["material_findings"][0]
        return (
            "Beacon found runtime degradation signals but cannot rank a root cause yet. "
            f"Highest-signal finding: {top.get('title')}."
        )

    return "Beacon did not detect major runtime degradation in the provided signals."
