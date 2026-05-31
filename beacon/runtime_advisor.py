import yaml

from beacon.diagnose.kafka.signals import KafkaRuntimeSignal


def finding(
    severity,
    title,
    impact,
    recommendation,
    file,
    rule_id="runtime.snapshot.diagnostic",
    domain="kafka",
    category="runtime_stability",
    evidence=None,
    tags=None,
    confidence=None,
):
    result = {
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

    if confidence:
        result["confidence"] = confidence

    return result


def analyze_runtime_file(path: str):
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    kafka_runtime = data.get("kafka_runtime", {})
    return evaluate_kafka_runtime(kafka_runtime, path)


def evaluate_kafka_runtime(runtime, file):
    findings = []
    signal = KafkaRuntimeSignal.from_snapshot(runtime)
    signal_evidence = signal.evidence()

    disk_usage = signal.broker_disk_usage_percent
    broker_disk_usage_by_broker = signal.broker_disk_usage_by_broker or {}
    disk_growth_7d = signal.disk_growth_percent_7d
    retention_bytes_configured = signal.retention_bytes_configured
    cleanup_policy_configured = signal.cleanup_policy_configured
    producer_rate_increased = signal.producer_rate_increased
    producer_error_rate_percent = signal.producer_error_rate_percent
    consumer_lag_increasing = signal.consumer_lag_increasing
    consumer_group_state = (signal.consumer_group_state or "").upper()
    active_members = signal.active_members
    expected_members = signal.expected_members
    rebalance_count_15m = signal.rebalance_count_15m
    avg_message_size_increased = signal.avg_message_size_increased
    under_replicated_partitions = signal.under_replicated_partitions
    under_min_isr_partitions = signal.under_min_isr_partitions
    offline_partitions = signal.offline_partitions
    leader_imbalance_percent = signal.leader_imbalance_percent
    active_controller_count = signal.active_controller_count
    controller_change_count_15m = signal.controller_change_count_15m
    partition_reassignment_count = signal.partition_reassignment_count
    replication_fetcher_lag = signal.replication_fetcher_lag
    request_latency_p95_ms = signal.request_latency_p95_ms
    request_queue_utilization_percent = signal.request_queue_utilization_percent
    network_io_utilization_percent = signal.network_io_utilization_percent
    produce_throttle_time_ms = signal.produce_throttle_time_ms
    fetch_throttle_time_ms = signal.fetch_throttle_time_ms
    schema_registry_available = signal.schema_registry_available
    schema_incompatible_changes_24h = signal.schema_incompatible_changes_24h
    estimated_replay_hours = signal.estimated_replay_hours
    replay_target_hours = signal.replay_target_hours
    retention_remaining_hours = signal.retention_remaining_hours
    broker_count = signal.broker_count
    partition_count = signal.partition_count
    replication_factor = signal.replication_factor

    if disk_usage is None:
        findings.append(
            finding(
                "ERROR",
                "Kafka runtime disk usage is missing",
                "Beacon cannot make runtime capacity decisions without broker disk usage.",
                "Provide broker_disk_usage_percent in runtime input.",
                file,
                rule_id="kafka.runtime.disk_usage.missing",
                evidence={"missing_signal": "broker_disk_usage_percent"},
                confidence="HIGH",
            )
        )
        return findings

    if disk_usage >= 90:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka broker disk usage is critically high: {disk_usage}%",
                "Kafka may become unstable if broker disks fill up. Produce requests, replication, and recovery can be affected.",
                "Take immediate capacity action: expand disk, reduce retention, delete obsolete topics, or move partitions away from hot brokers.",
                file,
                rule_id="kafka.runtime.disk_usage.critical",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    elif disk_usage >= 80:
        findings.append(
            finding(
                "HIGH",
                f"Kafka broker disk usage is above warning threshold: {disk_usage}%",
                "Disk usage above 80% indicates limited capacity buffer for traffic spikes, retention growth, or replication recovery.",
                "Analyze whether this is caused by capacity shortage, retention settings, producer volume, or consumer lag.",
                file,
                rule_id="kafka.runtime.disk_usage.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if broker_disk_usage_by_broker:
        max_broker = max(
            broker_disk_usage_by_broker, key=broker_disk_usage_by_broker.get
        )
        min_broker = min(
            broker_disk_usage_by_broker, key=broker_disk_usage_by_broker.get
        )
        max_usage = broker_disk_usage_by_broker[max_broker]
        min_usage = broker_disk_usage_by_broker[min_broker]

        if max_usage >= 90:
            findings.append(
                finding(
                    "CRITICAL",
                    f"Kafka broker '{max_broker}' disk usage is critically high: {max_usage}%",
                    "A single broker can fail or reject writes even when aggregate cluster disk usage looks acceptable.",
                    "Create broker-specific headroom, inspect partition placement, and move or reassign hot partitions.",
                    file,
                    rule_id="kafka.runtime.broker_disk_skew.critical",
                    evidence={
                        **signal_evidence,
                        "max_broker": max_broker,
                        "max_usage_percent": max_usage,
                    },
                    confidence="HIGH",
                )
            )

        if max_usage - min_usage >= 25:
            findings.append(
                finding(
                    "HIGH",
                    "Kafka broker disk usage is skewed across brokers",
                    "Uneven broker disk usage can cause one broker to saturate before the cluster appears full.",
                    "Review partition placement, topic retention, leader distribution, and reassignment needs.",
                    file,
                    rule_id="kafka.runtime.broker_disk_skew.high",
                    evidence={
                        **signal_evidence,
                        "max_broker": max_broker,
                        "min_broker": min_broker,
                        "skew_percent": max_usage - min_usage,
                    },
                    confidence="HIGH",
                )
            )

    if disk_usage >= 80 and retention_bytes_configured is False:
        findings.append(
            finding(
                "HIGH",
                "Kafka retention_bytes is not configured while disk usage is high",
                "Without retention_bytes, disk growth may depend only on time-based retention and producer volume.",
                "Set retention_bytes per topic based on broker disk capacity, expected throughput, and recovery requirements.",
                file,
                rule_id="kafka.runtime.retention_bytes.missing_under_pressure",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if disk_usage >= 80 and cleanup_policy_configured is False:
        findings.append(
            finding(
                "MEDIUM",
                "Kafka cleanup policy is not explicitly configured while disk usage is high",
                "Unclear cleanup behavior makes disk usage less predictable during traffic spikes.",
                "Explicitly configure cleanup_policy as delete, compact, or compact,delete depending on topic purpose.",
                file,
                rule_id="kafka.runtime.cleanup_policy.missing_under_pressure",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if disk_usage >= 80 and disk_growth_7d is not None and disk_growth_7d >= 15:
        findings.append(
            finding(
                "HIGH",
                f"Kafka disk usage increased by {disk_growth_7d}% in 7 days",
                "Rapid disk growth suggests traffic, retention, message size, or cleanup behavior changed recently.",
                "Check recent deployments, producer throughput, message size, topic growth, and retention cleanup.",
                file,
                rule_id="kafka.runtime.disk_growth.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if disk_usage >= 80 and producer_rate_increased:
        findings.append(
            finding(
                "HIGH",
                "Kafka producer rate increased while disk usage is high",
                "Disk pressure may be driven by increased event volume rather than raw disk capacity shortage.",
                "Validate whether producer traffic increase is expected. Check recent producer deployments and event volume changes.",
                file,
                rule_id="kafka.runtime.producer_rate.increased_under_pressure",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if disk_usage >= 80 and avg_message_size_increased:
        findings.append(
            finding(
                "HIGH",
                "Kafka average message size increased while disk usage is high",
                "Larger messages increase disk usage, network traffic, memory pressure, and consumer processing latency.",
                "Review producer payload changes. Move large payloads to object storage and publish references through Kafka.",
                file,
                rule_id="kafka.runtime.message_size.increased_under_pressure",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if disk_usage >= 80 and consumer_lag_increasing:
        findings.append(
            finding(
                "MEDIUM",
                "Kafka consumer lag is increasing during disk pressure",
                "Consumer lag can increase retained data volume and delay cleanup impact visibility.",
                "Check consumer processing latency, database calls, external API calls, retry behavior, and poison messages.",
                file,
                rule_id="kafka.runtime.consumer_lag.increasing_under_pressure",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if offline_partitions is not None and offline_partitions > 0:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {offline_partitions} offline partition(s)",
                "Offline partitions are unavailable for reads or writes and indicate active production impact.",
                "Identify affected brokers and partitions, restore broker health, and validate replica recovery.",
                file,
                rule_id="kafka.runtime.offline_partitions",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if under_replicated_partitions is not None and under_replicated_partitions > 0:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {under_replicated_partitions} under-replicated partitions",
                "Under-replicated partitions indicate broker, disk, network, or replication health issues.",
                "Investigate broker health, disk I/O, network latency, ISR shrink, and partition leadership distribution.",
                file,
                rule_id="kafka.runtime.under_replicated_partitions",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if under_min_isr_partitions is not None and under_min_isr_partitions > 0:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {under_min_isr_partitions} partition(s) below min ISR",
                "Partitions below min ISR can reject acks=all writes or weaken durability during broker failure.",
                "Restore ISR health, inspect slow replicas, disk I/O, network latency, and broker placement.",
                file,
                rule_id="kafka.runtime.under_min_isr_partitions",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if leader_imbalance_percent is not None and leader_imbalance_percent >= 50:
        findings.append(
            finding(
                "HIGH",
                f"Kafka leader distribution is imbalanced: {leader_imbalance_percent}%",
                "Leader imbalance can overload a subset of brokers and create uneven request latency.",
                "Review partition leadership, preferred leader election safety, and broker load distribution.",
                file,
                rule_id="kafka.runtime.leader_imbalance.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if active_controller_count is not None and active_controller_count != 1:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka active controller count is invalid: {active_controller_count}",
                "Kafka should have exactly one active controller. Zero or multiple active controllers indicate cluster control-plane instability.",
                "Investigate controller election, broker quorum health, ZooKeeper/KRaft health, and recent broker restarts.",
                file,
                rule_id="kafka.runtime.controller_count.invalid",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if controller_change_count_15m is not None and controller_change_count_15m >= 2:
        findings.append(
            finding(
                "HIGH",
                f"Kafka controller changed {controller_change_count_15m} times in 15 minutes",
                "Frequent controller changes can destabilize metadata operations, partition leadership, and broker recovery.",
                "Inspect broker churn, controller logs, quorum health, GC pauses, and network instability.",
                file,
                rule_id="kafka.runtime.controller_churn.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if partition_reassignment_count is not None and partition_reassignment_count > 0:
        findings.append(
            finding(
                "MEDIUM",
                f"Kafka has {partition_reassignment_count} partition reassignment(s) in progress",
                "Reassignments consume broker, network, and disk capacity and can amplify incidents if run during saturation.",
                "Validate reassignment throttle, broker headroom, and incident safety before continuing.",
                file,
                rule_id="kafka.runtime.partition_reassignment.active",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if replication_fetcher_lag is not None and replication_fetcher_lag >= 10000:
        findings.append(
            finding(
                "HIGH",
                f"Kafka replication fetcher lag is high: {replication_fetcher_lag}",
                "Replica fetcher lag can delay ISR recovery and increase failover or data-loss exposure.",
                "Inspect follower broker disk, network, inter-broker throttles, and replication fetcher health.",
                file,
                rule_id="kafka.runtime.replication_fetcher_lag.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if rebalance_count_15m is not None and rebalance_count_15m >= 3:
        findings.append(
            finding(
                "HIGH",
                f"Kafka consumer group rebalanced {rebalance_count_15m} times in 15 minutes",
                "Frequent rebalances can stall consumption and amplify lag during incidents.",
                "Inspect deployment churn, heartbeat/session timeouts, max.poll settings, and consumer crashes.",
                file,
                rule_id="kafka.runtime.rebalance_storm",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if consumer_group_state in {
        "REBALANCING",
        "PREPARING_REBALANCE",
        "COMPLETING_REBALANCE",
    }:
        findings.append(
            finding(
                "HIGH",
                f"Kafka consumer group is unstable: {consumer_group_state}",
                "Consumer group instability can pause processing and increase end-to-end latency.",
                "Review member churn, consumer logs, polling behavior, session timeout, and recent deploys.",
                file,
                rule_id="kafka.runtime.consumer_group.unstable",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if active_members == 0 and consumer_lag_increasing:
        findings.append(
            finding(
                "HIGH",
                "Kafka consumer group has no active members while lag is increasing",
                "No active consumers means backlog can grow without processing.",
                "Restore consumer deployment health, check scaling targets, and verify consumer group membership.",
                file,
                rule_id="kafka.runtime.consumer_group.no_active_members",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if (
        expected_members
        and active_members is not None
        and active_members < expected_members
    ):
        findings.append(
            finding(
                "MEDIUM",
                "Kafka consumer group has fewer active members than expected",
                "Reduced consumer membership lowers processing capacity and can trigger lag growth.",
                "Check consumer pod/process health, autoscaling, deployment rollout, and assignment balance.",
                file,
                rule_id="kafka.runtime.consumer_group.member_shortfall",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if producer_error_rate_percent is not None and producer_error_rate_percent >= 5:
        findings.append(
            finding(
                "HIGH",
                f"Kafka producer error rate is high: {producer_error_rate_percent}%",
                "Producer errors can indicate broker throttling, serialization failures, auth issues, or network instability.",
                "Inspect producer error classes, broker request errors, throttling, auth, and recent producer deployments.",
                file,
                rule_id="kafka.runtime.producer_error_rate.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if request_latency_p95_ms is not None and request_latency_p95_ms >= 500:
        findings.append(
            finding(
                "HIGH",
                f"Kafka request p95 latency is high: {request_latency_p95_ms}ms",
                "High request latency can slow producers, consumers, replication, and controller operations.",
                "Inspect broker CPU, disk I/O, network, request queues, throttling, and hot partitions.",
                file,
                rule_id="kafka.runtime.request_latency.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if (
        request_queue_utilization_percent is not None
        and request_queue_utilization_percent >= 80
    ):
        findings.append(
            finding(
                "HIGH",
                f"Kafka request queue utilization is high: {request_queue_utilization_percent}%",
                "Request queue saturation can increase producer, consumer, and replication latency.",
                "Inspect broker CPU, network processors, disk I/O, request handlers, and hot clients.",
                file,
                rule_id="kafka.runtime.request_queue_saturation.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if (
        network_io_utilization_percent is not None
        and network_io_utilization_percent >= 85
    ):
        findings.append(
            finding(
                "HIGH",
                f"Kafka network I/O utilization is high: {network_io_utilization_percent}%",
                "Network saturation can slow replication, increase consumer lag, and destabilize brokers.",
                "Review broker network throughput, cross-AZ replication, client traffic, and compression settings.",
                file,
                rule_id="kafka.runtime.network_saturation.high",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if produce_throttle_time_ms is not None and produce_throttle_time_ms >= 100:
        findings.append(
            finding(
                "MEDIUM",
                f"Kafka producer throttle time is elevated: {produce_throttle_time_ms}ms",
                "Producer throttling can indicate quota pressure or overloaded brokers.",
                "Review producer quotas, broker load, client traffic spikes, and whether throttling is expected.",
                file,
                rule_id="kafka.runtime.producer_throttle.high",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if fetch_throttle_time_ms is not None and fetch_throttle_time_ms >= 100:
        findings.append(
            finding(
                "MEDIUM",
                f"Kafka fetch throttle time is elevated: {fetch_throttle_time_ms}ms",
                "Consumer fetch throttling can slow processing and contribute to lag growth.",
                "Review consumer quotas, broker load, client traffic spikes, and whether throttling is expected.",
                file,
                rule_id="kafka.runtime.fetch_throttle.high",
                evidence=signal_evidence,
                confidence="MEDIUM",
            )
        )

    if schema_registry_available is False:
        findings.append(
            finding(
                "HIGH",
                "Kafka Schema Registry is unavailable",
                "Schema Registry unavailability can block producers or consumers that validate schemas at runtime.",
                "Restore Schema Registry health and verify producer and consumer fallback behavior.",
                file,
                rule_id="kafka.runtime.schema_registry.unavailable",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if (
        schema_incompatible_changes_24h is not None
        and schema_incompatible_changes_24h > 0
    ):
        findings.append(
            finding(
                "HIGH",
                f"Kafka saw {schema_incompatible_changes_24h} incompatible schema change(s) in 24h",
                "Incompatible schema changes can break consumers and cause poison-message style incidents.",
                "Review schema compatibility mode, producer deployment diff, and affected consumers before rollout.",
                file,
                rule_id="kafka.runtime.schema_incompatible_changes",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )

    if estimated_replay_hours == float("inf"):
        findings.append(
            finding(
                "CRITICAL",
                "Kafka backlog cannot be replayed at current throughput",
                "Consumer throughput is not exceeding producer rate, so backlog will not drain without intervention.",
                "Increase safe consumer throughput, reduce producer intake, fix downstream bottlenecks, or pause non-critical producers.",
                file,
                rule_id="kafka.runtime.replay.no_drain_capacity",
                evidence=signal_evidence,
                confidence="HIGH",
            )
        )
    elif (
        estimated_replay_hours is not None
        and replay_target_hours is not None
        and estimated_replay_hours > replay_target_hours
    ):
        findings.append(
            finding(
                "HIGH",
                f"Kafka backlog replay time exceeds target: {estimated_replay_hours:.2f}h",
                "The current backlog may take longer to drain than the operational recovery target allows.",
                "Increase consumer capacity, remove downstream bottlenecks, reduce producer rate, or revisit replay SLOs.",
                file,
                rule_id="kafka.runtime.replay.time_exceeds_target",
                evidence={
                    **signal_evidence,
                    "estimated_replay_hours": round(estimated_replay_hours, 2),
                },
                confidence="HIGH",
            )
        )

    if (
        estimated_replay_hours is not None
        and estimated_replay_hours != float("inf")
        and retention_remaining_hours is not None
        and estimated_replay_hours > retention_remaining_hours
    ):
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka retention may expire before replay completes: {estimated_replay_hours:.2f}h replay",
                "Backlog recovery is estimated to take longer than the remaining retention window, creating data-loss risk.",
                "Extend retention, create capacity headroom, accelerate consumers, or reduce producer intake before data ages out.",
                file,
                rule_id="kafka.runtime.replay.retention_window_insufficient",
                evidence={
                    **signal_evidence,
                    "estimated_replay_hours": round(estimated_replay_hours, 2),
                },
                confidence="HIGH",
            )
        )

    if broker_count and partition_count and replication_factor:
        replica_load = partition_count * replication_factor

        if replica_load / broker_count > 1000:
            findings.append(
                finding(
                    "HIGH",
                    "Kafka broker partition replica load is high",
                    "Too many replicas per broker can increase disk, memory, controller, and recovery pressure.",
                    "Review partition strategy, topic count, broker count, and whether additional brokers are needed.",
                    file,
                    rule_id="kafka.runtime.replica_load.high",
                    evidence={
                        **signal_evidence,
                        "replicas_per_broker": replica_load / broker_count,
                        "review_threshold": 1000,
                    },
                    confidence="HIGH",
                )
            )

    decision = decide_action(signal)

    findings.append(
        finding(
            decision["severity"],
            decision["title"],
            decision["impact"],
            decision["recommendation"],
            file,
            rule_id=decision["rule_id"],
            evidence=decision["evidence"],
            confidence=decision["confidence"],
        )
    )

    return findings


def decide_action(signal):
    disk_usage = signal.broker_disk_usage_percent or 0
    disk_growth_7d = signal.disk_growth_percent_7d or 0
    evidence = signal.evidence()

    if disk_usage >= 90:
        return {
            "severity": "CRITICAL",
            "title": "Decision: Take immediate Kafka capacity protection action",
            "impact": "Disk usage is already in a critical range. Waiting for perfect root cause analysis can increase outage risk.",
            "recommendation": "Immediately create headroom by expanding disk or reducing retention, then investigate producer volume, message size, and consumer lag.",
            "rule_id": "kafka.runtime.decision.capacity_protection",
            "evidence": evidence,
            "confidence": "HIGH",
        }

    if disk_usage >= 80 and signal.has_workload_change:
        return {
            "severity": "HIGH",
            "title": "Decision: Investigate producer/consumer behavior before only expanding disk",
            "impact": "Disk pressure appears linked to workload behavior such as producer volume, message size, or consumer lag.",
            "recommendation": "Check recent code deployments, producer payload changes, consumer processing latency, retries, and lag by partition. Expand disk only if growth remains after workload correction.",
            "rule_id": "kafka.runtime.decision.workload_investigation",
            "evidence": evidence,
            "confidence": "MEDIUM",
        }

    if disk_usage >= 80 and signal.has_weak_storage_guardrails:
        return {
            "severity": "HIGH",
            "title": "Decision: Optimize Kafka retention and cleanup before expanding disk",
            "impact": "Disk pressure may be caused by missing storage guardrails rather than genuine capacity shortage.",
            "recommendation": "Configure retention_bytes, cleanup_policy, and topic-level storage limits. Recalculate disk capacity after applying guardrails.",
            "rule_id": "kafka.runtime.decision.retention_cleanup",
            "evidence": evidence,
            "confidence": "HIGH",
        }

    if (
        disk_usage >= 80
        and not signal.has_weak_storage_guardrails
        and not signal.has_workload_change
        and disk_growth_7d < 10
    ):
        return {
            "severity": "MEDIUM",
            "title": "Decision: Expand Kafka disk capacity",
            "impact": "Disk usage is high while configuration and workload signals appear stable.",
            "recommendation": "Plan disk expansion or broker capacity increase. Keep retention guardrails in place and monitor growth trend.",
            "rule_id": "kafka.runtime.decision.disk_expansion",
            "evidence": evidence,
            "confidence": "MEDIUM",
        }

    return {
        "severity": "LOW",
        "title": "Decision: Monitor Kafka disk capacity",
        "impact": "Runtime signals do not currently indicate urgent disk risk.",
        "recommendation": "Continue monitoring disk growth, producer rate, message size, consumer lag, and under-replicated partitions.",
        "rule_id": "kafka.runtime.decision.monitor_capacity",
        "evidence": evidence,
        "confidence": "LOW",
    }
