import yaml

from beacon.diagnose.kafka.signals import KafkaRuntimeSignal


def finding(
    severity,
    title,
    impact,
    recommendation,
    file,
    rule_id="runtime.snapshot.diagnostic",
    domain="runtime",
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
    disk_growth_7d = signal.disk_growth_percent_7d
    retention_bytes_configured = signal.retention_bytes_configured
    cleanup_policy_configured = signal.cleanup_policy_configured
    producer_rate_increased = signal.producer_rate_increased
    consumer_lag_increasing = signal.consumer_lag_increasing
    avg_message_size_increased = signal.avg_message_size_increased
    under_replicated_partitions = signal.under_replicated_partitions
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
