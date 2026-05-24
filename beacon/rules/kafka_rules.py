from beacon.rules.models import finding

from beacon.engine.registry import register_rule
from beacon.engine.rule_model import Rule
def evaluate_kafka_config(data, file):
    findings = []
    topics = data.get("topics", [])

    for topic in topics:
        name = topic.get("name", "unknown-topic")

        rf = topic.get("replication_factor")
        partitions = topic.get("partitions")
        retention_ms = topic.get("retention_ms")
        retention_bytes = topic.get("retention_bytes")
        cleanup_policy = topic.get("cleanup_policy")
        min_isr = topic.get("min_insync_replicas")
        segment_bytes = topic.get("segment_bytes")
        max_message_bytes = topic.get("max_message_bytes")

        if rf is not None and rf < 3:
            findings.append(
                finding(
                    rule_id="kafka.topic.replication_factor.low",
                    domain="kafka",
                    category="resiliency",
                    severity="CRITICAL",
                    title=f"Kafka topic '{name}' has replication factor {rf}",
                    impact="A broker failure can make this topic unavailable and interrupt production workflows.",
                    recommendation="Use replication_factor=3 for production topics.",
                    file=file,
                    evidence={
                        "topic": name,
                        "replication_factor": rf,
                        "expected_minimum": 3,
                    },
                    tags=["availability", "resiliency", "production-readiness"],
                )
            )

        if partitions is not None and partitions < 3:
            findings.append(
                finding(
                    rule_id="kafka.topic.partitions.low",
                    domain="kafka",
                    category="scalability",
                    severity="HIGH",
                    title=f"Kafka topic '{name}' has low partition count",
                    impact="Low partitions can limit consumer parallelism and reduce throughput.",
                    recommendation="Use at least 3 partitions for production workloads, then tune based on throughput.",
                    file=file,
                    evidence={
                        "topic": name,
                        "partitions": partitions,
                        "expected_minimum": 3,
                    },
                    tags=["throughput", "parallelism", "scalability"],
                )
            )

        if retention_ms is not None and retention_ms < 86400000:
            findings.append(
                finding(
                    rule_id="kafka.topic.retention_ms.low",
                    domain="kafka",
                    category="recovery_readiness",
                    severity="MEDIUM",
                    title=f"Kafka topic '{name}' retention is below 24 hours",
                    impact="Short retention reduces replay capability during incidents.",
                    recommendation="Increase retention based on recovery and audit requirements.",
                    file=file,
                    evidence={
                        "topic": name,
                        "retention_ms": retention_ms,
                        "expected_minimum_ms": 86400000,
                    },
                    tags=["replay", "recovery", "retention"],
                )
            )

        if cleanup_policy is None:
            findings.append(
                finding(
                    rule_id="kafka.topic.cleanup_policy.missing",
                    domain="kafka",
                    category="storage_sustainability",
                    severity="MEDIUM",
                    title=f"Kafka topic '{name}' does not define cleanup policy",
                    impact="Undefined cleanup policy may create unpredictable retention and disk behavior.",
                    recommendation="Explicitly configure cleanup_policy as delete, compact, or compact,delete.",
                    file=file,
                    evidence={"topic": name, "cleanup_policy": cleanup_policy},
                    tags=["storage", "cleanup", "retention"],
                )
            )

        if min_isr is None:
            findings.append(
                finding(
                    rule_id="kafka.topic.min_insync_replicas.missing",
                    domain="kafka",
                    category="resiliency",
                    severity="HIGH",
                    title=f"Kafka topic '{name}' does not define min.insync.replicas",
                    impact="Missing min ISR configuration can weaken durability guarantees during broker failure.",
                    recommendation="Configure min.insync.replicas for production topics.",
                    file=file,
                    evidence={"topic": name, "min_insync_replicas": min_isr},
                    tags=["durability", "resiliency", "isr"],
                )
            )

        if retention_bytes is None:
            findings.append(
                finding(
                    rule_id="kafka.topic.retention_bytes.missing",
                    domain="kafka",
                    category="storage_sustainability",
                    severity="HIGH",
                    title=f"Kafka topic '{name}' does not define retention_bytes",
                    impact="Disk usage can grow unpredictably if producer volume increases or cleanup is delayed.",
                    recommendation="Set retention_bytes based on broker disk capacity, expected throughput, and recovery needs.",
                    file=file,
                    evidence={"topic": name, "retention_bytes": retention_bytes},
                    tags=["storage", "capacity", "retention"],
                )
            )

        if rf is not None and partitions is not None:
            storage_units = rf * partitions

            if storage_units >= 30:
                findings.append(
                    finding(
                        rule_id="kafka.topic.storage_multiplier.high",
                        domain="kafka",
                        category="storage_sustainability",
                        severity="HIGH",
                        title=(
                            f"Kafka topic '{name}' has high storage multiplier: "
                            f"partitions({partitions}) x replication_factor({rf}) = {storage_units}"
                        ),
                        impact="High partition and replica count increases broker disk usage, replication traffic, and recovery load.",
                        recommendation="Validate broker disk capacity, partition distribution, and expected data volume.",
                        file=file,
                        evidence={
                            "topic": name,
                            "partitions": partitions,
                            "replication_factor": rf,
                            "storage_multiplier": storage_units,
                        },
                        tags=["storage", "replication", "capacity"],
                    )
                )

            elif storage_units >= 15:
                findings.append(
                    finding(
                        rule_id="kafka.topic.storage_multiplier.moderate",
                        domain="kafka",
                        category="storage_sustainability",
                        severity="MEDIUM",
                        title=(
                            f"Kafka topic '{name}' has moderate storage multiplier: "
                            f"partitions({partitions}) x replication_factor({rf}) = {storage_units}"
                        ),
                        impact="Replica storage grows with every partition and can increase disk pressure during traffic spikes.",
                        recommendation="Review whether partition count and replication factor match actual throughput needs.",
                        file=file,
                        evidence={
                            "topic": name,
                            "partitions": partitions,
                            "replication_factor": rf,
                            "storage_multiplier": storage_units,
                        },
                        tags=["storage", "capacity", "replication"],
                    )
                )

        if max_message_bytes is not None and max_message_bytes > 1048576:
            findings.append(
                finding(
                    rule_id="kafka.topic.max_message_bytes.large",
                    domain="kafka",
                    category="storage_sustainability",
                    severity="HIGH",
                    title=f"Kafka topic '{name}' allows messages larger than 1MB",
                    impact="Large messages increase broker disk I/O, memory pressure, network usage, and consumer processing latency.",
                    recommendation="Keep Kafka messages small where possible; store large payloads externally and pass references through Kafka.",
                    file=file,
                    evidence={
                        "topic": name,
                        "max_message_bytes": max_message_bytes,
                        "recommended_max_bytes": 1048576,
                    },
                    tags=["message-size", "latency", "storage"],
                )
            )

        if segment_bytes is not None and segment_bytes > 1073741824:
            findings.append(
                finding(
                    rule_id="kafka.topic.segment_bytes.large",
                    domain="kafka",
                    category="storage_sustainability",
                    severity="MEDIUM",
                    title=f"Kafka topic '{name}' has segment_bytes greater than 1GB",
                    impact="Large log segments can delay cleanup and make disk recovery behavior less predictable.",
                    recommendation="Use segment size based on retention, cleanup frequency, and operational recovery needs.",
                    file=file,
                    evidence={
                        "topic": name,
                        "segment_bytes": segment_bytes,
                        "recommended_max_bytes": 1073741824,
                    },
                    tags=["segment", "cleanup", "storage"],
                )
            )

        if cleanup_policy == "compact" and retention_bytes is None:
            findings.append(
                finding(
                    rule_id="kafka.topic.compacted_without_retention_bytes",
                    domain="kafka",
                    category="storage_sustainability",
                    severity="MEDIUM",
                    title=f"Kafka compacted topic '{name}' has no retention_bytes limit",
                    impact="Compacted topics can still consume significant disk if key cardinality is high or tombstone cleanup is delayed.",
                    recommendation="Set retention_bytes or review compaction and key cardinality assumptions.",
                    file=file,
                    evidence={
                        "topic": name,
                        "cleanup_policy": cleanup_policy,
                        "retention_bytes": retention_bytes,
                    },
                    tags=["compaction", "storage", "retention"],
                )
            )

    return findings

def replication_factor_rule(resource, context):
    findings = []

    rf = resource.get("replication_factor")
    name = resource.get("name")

    if rf is not None and rf < 3:
        findings.append(
            finding(
                rule_id="kafka.topic.replication_factor.low",
                domain="kafka",
                category="resiliency",
                severity="CRITICAL",
                title=(
                    f"Kafka topic '{name}' has "
                    f"replication factor {rf}"
                ),
                impact=(
                    "A broker failure can make "
                    "this topic unavailable."
                ),
                recommendation=(
                    "Use replication_factor=3 "
                    "for production topics."
                ),
                file=context["file"],
                evidence={
                    "topic": name,
                    "replication_factor": rf,
                    "expected_minimum": 3,
                },
                tags=[
                    "availability",
                    "resiliency",
                ],
            )
        )

    return findings

register_rule(
    Rule(
        rule_id="kafka.topic.replication_factor.low",
        domain="kafka",
        category="resiliency",
        severity="CRITICAL",
        title="Kafka replication factor too low",
        evaluator=replication_factor_rule,
        supported_types=["kafka_topic"],
        tags=[
            "availability",
            "resiliency",
        ],
    )
)
