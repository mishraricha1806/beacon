from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_kafka_finding(
    resource,
    rule_id,
    category,
    severity,
    title,
    impact,
    recommendation,
    evidence,
    tags=None,
):
    return Finding(
        rule_id=rule_id,
        domain="kafka",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def broker_default_replication_factor_low(resource, context):
    value = resource.attributes.get("default_replication_factor")

    if value is None or value >= 3:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.default_replication_factor.low",
        "resiliency",
        "HIGH",
        f"Kafka broker '{resource.name}' has low default replication factor",
        "Low default replication factor can create under-replicated topics when topics are auto-created or created without explicit replication settings.",
        "Use default.replication.factor=3 for production Kafka clusters.",
        {
            "broker": resource.name,
            "default_replication_factor": value,
            "expected_minimum": 3,
        },
        ["kafka", "broker", "resiliency"],
    )


def broker_offsets_replication_factor_low(resource, context):
    value = resource.attributes.get("offsets_topic_replication_factor")

    if value is None or value >= 3:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.offsets_replication_factor.low",
        "resiliency",
        "HIGH",
        f"Kafka broker '{resource.name}' has low offsets topic replication factor",
        "Low offsets topic replication can weaken consumer group recovery during broker failure.",
        "Use offsets.topic.replication.factor=3 for production Kafka clusters.",
        {
            "broker": resource.name,
            "offsets_topic_replication_factor": value,
            "expected_minimum": 3,
        },
        ["kafka", "broker", "consumer-groups"],
    )


def broker_transaction_log_replication_factor_low(resource, context):
    value = resource.attributes.get("transaction_state_log_replication_factor")

    if value is None or value >= 3:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.transaction_log_replication_factor.low",
        "resiliency",
        "HIGH",
        f"Kafka broker '{resource.name}' has low transaction state log replication factor",
        "Low transaction state log replication can weaken exactly-once and transactional producer recovery.",
        "Use transaction.state.log.replication.factor=3 for production Kafka clusters.",
        {
            "broker": resource.name,
            "transaction_state_log_replication_factor": value,
            "expected_minimum": 3,
        },
        ["kafka", "broker", "transactions"],
    )


def broker_auto_create_topics_enabled(resource, context):
    value = resource.attributes.get("auto_create_topics_enable")

    if value is not True:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.auto_create_topics.enabled",
        "operational_safety",
        "MEDIUM",
        f"Kafka broker '{resource.name}' allows automatic topic creation",
        "Automatic topic creation can bypass production topic standards for replication, partitions, retention, and ownership.",
        "Disable auto.create.topics.enable in production or enforce strict topic creation controls.",
        {"broker": resource.name, "auto_create_topics_enable": value},
        ["kafka", "broker", "governance"],
    )


def broker_unclean_leader_election_enabled(resource, context):
    value = resource.attributes.get("unclean_leader_election_enable")

    if value is not True:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.unclean_leader_election.enabled",
        "resiliency",
        "CRITICAL",
        f"Kafka broker '{resource.name}' allows unclean leader election",
        "Unclean leader election can restore availability by sacrificing acknowledged data during replica failure.",
        "Disable unclean.leader.election.enable for production clusters unless an explicit data-loss exception exists.",
        {"broker": resource.name, "unclean_leader_election_enable": value},
        ["kafka", "broker", "data-loss"],
    )


def broker_rack_missing(resource, context):
    rack = resource.attributes.get("broker_rack")

    if rack:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.rack_awareness.missing",
        "resiliency",
        "HIGH",
        f"Kafka broker '{resource.name}' has no broker.rack configured",
        "Missing rack awareness can place replicas in the same failure domain and weaken AZ survivability.",
        "Set broker.rack and validate replica placement across failure domains.",
        {"broker": resource.name, "broker_rack": rack},
        ["kafka", "broker", "rack-awareness"],
    )


def broker_plaintext_listener_enabled(resource, context):
    protocol = resource.attributes.get("security_protocol")
    listener_map = resource.attributes.get("listener_security_protocol_map")
    text = f"{protocol or ''} {listener_map or ''}".upper()

    if "PLAINTEXT" not in text:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.security.plaintext_listener",
        "operational_safety",
        "HIGH",
        f"Kafka broker '{resource.name}' exposes PLAINTEXT listener configuration",
        "Plaintext Kafka traffic can expose credentials and event payloads on production networks.",
        "Use SSL or SASL_SSL listeners for production traffic and restrict plaintext listeners to approved internal exceptions.",
        {
            "broker": resource.name,
            "security_protocol": protocol,
            "listener_security_protocol_map": listener_map,
        },
        ["kafka", "security", "tls"],
    )


def broker_authorizer_missing(resource, context):
    authorizer = resource.attributes.get("authorizer_class_name")

    if authorizer:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.security.authorizer_missing",
        "operational_safety",
        "HIGH",
        f"Kafka broker '{resource.name}' has no authorizer configured",
        "Missing Kafka authorization can allow broad topic, group, or cluster access if network controls fail.",
        "Enable Kafka authorization and define least-privilege ACLs or equivalent platform controls.",
        {"broker": resource.name, "authorizer_class_name": authorizer},
        ["kafka", "security", "acl"],
    )


def broker_allow_everyone_if_no_acl(resource, context):
    value = resource.attributes.get("allow_everyone_if_no_acl_found")

    if value is not True:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.security.allow_everyone_if_no_acl",
        "operational_safety",
        "CRITICAL",
        f"Kafka broker '{resource.name}' allows access when no ACL is found",
        "allow.everyone.if.no.acl.found can turn missing ACLs into broad access.",
        "Set allow.everyone.if.no.acl.found=false and explicitly grant required ACLs.",
        {"broker": resource.name, "allow_everyone_if_no_acl_found": value},
        ["kafka", "security", "acl"],
    )


def broker_controlled_shutdown_disabled(resource, context):
    value = resource.attributes.get("controlled_shutdown_enable")

    if value is not False:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.controlled_shutdown.disabled",
        "recovery_readiness",
        "MEDIUM",
        f"Kafka broker '{resource.name}' has controlled shutdown disabled",
        "Disabled controlled shutdown can increase partition leadership disruption during broker maintenance.",
        "Enable controlled shutdown where supported and validate rolling restart procedures.",
        {"broker": resource.name, "controlled_shutdown_enable": value},
        ["kafka", "broker", "maintenance"],
    )


def broker_client_quotas_missing(resource, context):
    producer_quota = resource.attributes.get("producer_quota_bytes_per_second")
    consumer_quota = resource.attributes.get("consumer_quota_bytes_per_second")

    if producer_quota is not None and consumer_quota is not None:
        return None

    return build_kafka_finding(
        resource,
        "kafka.broker.client_quotas.missing",
        "operational_safety",
        "MEDIUM",
        f"Kafka broker '{resource.name}' does not define both producer and consumer quotas",
        "Missing client quotas can allow one workload to saturate brokers during spikes or incidents.",
        "Define producer and consumer quotas for production clients or document approved no-quota exceptions.",
        {
            "broker": resource.name,
            "producer_quota_bytes_per_second": producer_quota,
            "consumer_quota_bytes_per_second": consumer_quota,
        },
        ["kafka", "quotas", "multi-tenant"],
    )


def replication_factor_low(resource, context):
    rf = resource.attributes.get("replication_factor")

    if rf is None or rf >= 3:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.replication_factor.low",
        category="resiliency",
        severity="CRITICAL",
        title=f"Kafka topic '{resource.name}' has replication factor {rf}",
        impact="A broker failure can make this topic unavailable and interrupt production workflows.",
        recommendation="Use replication_factor=3 for production Kafka topics.",
        evidence={
            "topic": resource.name,
            "replication_factor": rf,
            "expected_minimum": 3,
        },
        tags=["kafka", "availability", "production-readiness"],
    )


def min_insync_replicas_missing(resource, context):
    min_isr = resource.attributes.get("min_insync_replicas")

    if min_isr is not None:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.min_insync_replicas.missing",
        category="resiliency",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' does not define min.insync.replicas",
        impact="Missing min ISR configuration can weaken durability guarantees during broker failure.",
        recommendation="Configure min.insync.replicas for production Kafka topics.",
        evidence={
            "topic": resource.name,
            "min_insync_replicas": min_isr,
        },
        tags=["kafka", "durability", "isr"],
    )


def min_insync_replicas_unsafe(resource, context):
    min_isr = resource.attributes.get("min_insync_replicas")
    rf = resource.attributes.get("replication_factor")

    if min_isr is None:
        return None

    if rf is not None and rf >= 3 and min_isr < 2:
        return build_kafka_finding(
            resource=resource,
            rule_id="kafka.topic.min_insync_replicas.unsafe",
            category="resiliency",
            severity="HIGH",
            title=f"Kafka topic '{resource.name}' has unsafe min.insync.replicas",
            impact="Low min ISR can allow writes with insufficient replica acknowledgement.",
            recommendation="For replication_factor=3, use min.insync.replicas=2 for production durability.",
            evidence={
                "topic": resource.name,
                "replication_factor": rf,
                "min_insync_replicas": min_isr,
                "recommended_minimum": 2,
            },
            tags=["kafka", "durability", "resiliency"],
        )

    return None


def retention_bytes_missing(resource, context):
    retention_bytes = resource.attributes.get("retention_bytes")

    if retention_bytes is not None:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.retention_bytes.missing",
        category="storage_sustainability",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' does not define retention_bytes",
        impact="Disk usage can grow unpredictably if producer volume increases or cleanup is delayed.",
        recommendation="Set retention_bytes based on broker disk capacity, throughput, and recovery needs.",
        evidence={
            "topic": resource.name,
            "retention_bytes": retention_bytes,
        },
        tags=["kafka", "storage", "capacity"],
    )


def retention_bytes_large(resource, context):
    retention_bytes = resource.attributes.get("retention_bytes")

    if retention_bytes is None or retention_bytes <= 10 * 1024 * 1024 * 1024:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.retention_bytes.large",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' defines very large retention_bytes",
        impact="Very large retention_bytes may exhaust broker disk over time and increase recovery time.",
        recommendation="Review retention_bytes and consider tiered storage, shorter retention, or stronger capacity planning.",
        evidence={
            "topic": resource.name,
            "retention_bytes": retention_bytes,
            "review_threshold_bytes": 10 * 1024 * 1024 * 1024,
        },
        tags=["kafka", "storage", "retention"],
    )


def retention_ms_unbounded(resource, context):
    retention_ms = resource.attributes.get("retention_ms")

    if retention_ms != -1:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.retention_ms.unbounded",
        category="storage_sustainability",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' has unbounded retention",
        impact="Unbounded retention can cause uncontrolled storage growth and broker disk pressure.",
        recommendation="Define a bounded retention_ms policy for production topics.",
        evidence={
            "topic": resource.name,
            "retention_ms": retention_ms,
        },
        tags=["kafka", "storage", "retention"],
    )


def retention_ms_low(resource, context):
    retention_ms = resource.attributes.get("retention_ms")

    if retention_ms is None:
        return None

    if retention_ms == -1:
        return None

    if retention_ms >= 86400000:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.retention_ms.low",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' has low retention period",
        impact=(
            "Low retention may reduce replay capability and operational recovery "
            "during outages or downstream failures."
        ),
        recommendation=(
            "Validate retention_ms against operational replay and recovery requirements."
        ),
        evidence={
            "topic": resource.name,
            "retention_ms": retention_ms,
            "recommended_minimum_ms": 86400000,
        },
        tags=["kafka", "retention", "recovery"],
    )


def cleanup_policy_missing(resource, context):
    cleanup_policy = resource.attributes.get("cleanup_policy")

    if cleanup_policy is not None:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.cleanup_policy.missing",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' does not define cleanup policy",
        impact="Undefined cleanup policy may create unpredictable retention and disk behavior.",
        recommendation="Explicitly configure cleanup_policy as delete, compact, or compact,delete.",
        evidence={
            "topic": resource.name,
            "cleanup_policy": cleanup_policy,
        },
        tags=["kafka", "cleanup", "retention"],
    )


def max_message_bytes_large(resource, context):
    max_message_bytes = resource.attributes.get("max_message_bytes")

    if max_message_bytes is None or max_message_bytes <= 1048576:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.max_message_bytes.large",
        category="storage_sustainability",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' allows messages larger than 1MB",
        impact="Large messages increase broker disk I/O, memory pressure, network usage, and consumer latency.",
        recommendation="Keep Kafka messages small; store large payloads externally and pass references through Kafka.",
        evidence={
            "topic": resource.name,
            "max_message_bytes": max_message_bytes,
            "recommended_max_bytes": 1048576,
        },
        tags=["kafka", "message-size", "latency"],
    )


def partitions_low(resource, context):
    partitions = resource.attributes.get("partitions")

    if partitions is None or partitions >= 3:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.partitions.low",
        category="scalability",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' has low partition count",
        impact="Low partitions can limit consumer parallelism and reduce throughput.",
        recommendation="Use at least 3 partitions for production workloads, then tune based on throughput.",
        evidence={
            "topic": resource.name,
            "partitions": partitions,
            "expected_minimum": 3,
        },
        tags=["kafka", "throughput", "parallelism"],
    )


def partitions_high(resource, context):
    partitions = resource.attributes.get("partitions")

    if partitions is None or partitions <= 100:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.partitions.high",
        category="scalability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' has very high partition count",
        impact="Very high partition count can increase broker metadata load, recovery time, and rebalance cost.",
        recommendation="Validate whether partition count is justified by throughput and consumer parallelism needs.",
        evidence={
            "topic": resource.name,
            "partitions": partitions,
            "review_threshold": 100,
        },
        tags=["kafka", "partitioning", "scalability"],
    )


def storage_multiplier_high(resource, context):
    rf = resource.attributes.get("replication_factor")
    partitions = resource.attributes.get("partitions")

    if rf is None or partitions is None:
        return None

    storage_units = rf * partitions

    if storage_units < 30:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.storage_multiplier.high",
        category="storage_sustainability",
        severity="HIGH",
        title=(
            f"Kafka topic '{resource.name}' has high storage multiplier: "
            f"partitions({partitions}) x replication_factor({rf}) = {storage_units}"
        ),
        impact="High partition and replica count increases broker disk usage, replication traffic, and recovery load.",
        recommendation="Validate broker disk capacity, partition distribution, and expected data volume.",
        evidence={
            "topic": resource.name,
            "partitions": partitions,
            "replication_factor": rf,
            "storage_multiplier": storage_units,
        },
        tags=["kafka", "storage", "capacity"],
    )


def storage_multiplier_moderate(resource, context):
    rf = resource.attributes.get("replication_factor")
    partitions = resource.attributes.get("partitions")

    if rf is None or partitions is None:
        return None

    storage_units = rf * partitions

    if storage_units < 15 or storage_units >= 30:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.storage_multiplier.moderate",
        category="storage_sustainability",
        severity="MEDIUM",
        title=(
            f"Kafka topic '{resource.name}' has moderate storage multiplier: "
            f"partitions({partitions}) x replication_factor({rf}) = {storage_units}"
        ),
        impact="Replica storage grows with every partition and can increase disk pressure during traffic spikes.",
        recommendation="Review whether partition count and replication factor match actual throughput and recovery needs.",
        evidence={
            "topic": resource.name,
            "partitions": partitions,
            "replication_factor": rf,
            "storage_multiplier": storage_units,
        },
        tags=["kafka", "storage", "capacity"],
    )


def segment_bytes_large(resource, context):
    segment_bytes = resource.attributes.get("segment_bytes")

    if segment_bytes is None or segment_bytes <= 1073741824:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.segment_bytes.large",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' has segment_bytes greater than 1GB",
        impact="Large log segments can delay cleanup and make disk recovery behavior less predictable.",
        recommendation="Use segment size based on retention, cleanup frequency, and operational recovery needs.",
        evidence={
            "topic": resource.name,
            "segment_bytes": segment_bytes,
            "recommended_max_bytes": 1073741824,
        },
        tags=["kafka", "segment", "cleanup"],
    )


def message_size_relative_segment(resource, context):
    segment_bytes = resource.attributes.get("segment_bytes")
    max_message_bytes = resource.attributes.get("max_message_bytes")

    if segment_bytes is None or max_message_bytes is None:
        return None

    if max_message_bytes <= segment_bytes / 4:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.message_size_relative_segment",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka topic '{resource.name}' max.message.bytes is large relative to segment.bytes",
        impact="Very large messages relative to segment size can affect log segmentation and cleanup behavior.",
        recommendation="Adjust segment.bytes or limit message size to reasonable bounds.",
        evidence={
            "topic": resource.name,
            "segment_bytes": segment_bytes,
            "max_message_bytes": max_message_bytes,
        },
        tags=["kafka", "message-size", "segment"],
    )


def compacted_without_retention_bytes(resource, context):
    cleanup_policy = resource.attributes.get("cleanup_policy")
    retention_bytes = resource.attributes.get("retention_bytes")

    if cleanup_policy != "compact" or retention_bytes is not None:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.compacted_without_retention_bytes",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Kafka compacted topic '{resource.name}' has no retention_bytes limit",
        impact="Compacted topics can still consume significant disk if key cardinality is high or tombstone cleanup is delayed.",
        recommendation="Set retention_bytes or review compaction and key cardinality assumptions.",
        evidence={
            "topic": resource.name,
            "cleanup_policy": cleanup_policy,
            "retention_bytes": retention_bytes,
        },
        tags=["kafka", "compaction", "storage"],
    )


def schema_compatibility_unsafe(resource, context):
    compatibility = resource.attributes.get("schema_compatibility")

    if compatibility is None:
        return None

    normalized = str(compatibility).upper()

    if normalized not in {"NONE", "DISABLED"}:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.schema_compatibility.unsafe",
        category="operational_safety",
        severity="HIGH",
        title=f"Kafka topic '{resource.name}' has unsafe schema compatibility",
        impact="Disabled schema compatibility can break consumers during producer deployments and increase incident risk.",
        recommendation="Use BACKWARD, FULL, or an approved compatibility mode for production event schemas.",
        evidence={
            "topic": resource.name,
            "schema_compatibility": compatibility,
        },
        tags=["kafka", "schema", "deployment-safety"],
    )


def topic_owner_missing(resource, context):
    owner = resource.attributes.get("owner")

    if owner:
        return None

    return build_kafka_finding(
        resource=resource,
        rule_id="kafka.topic.owner.missing",
        category="operational_safety",
        severity="LOW",
        title=f"Kafka topic '{resource.name}' has no owner metadata",
        impact="Missing topic ownership slows incident routing, retention review, and cleanup decisions.",
        recommendation="Add owner/team metadata for production Kafka topics.",
        evidence={
            "topic": resource.name,
            "owner": owner,
        },
        tags=["kafka", "governance", "ownership"],
    )


def register(
    rule_id,
    category,
    severity,
    title,
    description,
    evaluator,
    tags,
    supported_resource_types=None,
):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="kafka",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=supported_resource_types or ["kafka_topic"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "kafka.broker.default_replication_factor.low",
    "resiliency",
    "HIGH",
    "Kafka broker default replication factor low",
    "Detects broker default replication factor below production-safe threshold.",
    broker_default_replication_factor_low,
    ["kafka", "broker", "resiliency"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.offsets_replication_factor.low",
    "resiliency",
    "HIGH",
    "Kafka broker offsets replication factor low",
    "Detects offsets topic replication factor below production-safe threshold.",
    broker_offsets_replication_factor_low,
    ["kafka", "broker", "consumer-groups"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.transaction_log_replication_factor.low",
    "resiliency",
    "HIGH",
    "Kafka broker transaction log replication factor low",
    "Detects transaction state log replication factor below production-safe threshold.",
    broker_transaction_log_replication_factor_low,
    ["kafka", "broker", "transactions"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.auto_create_topics.enabled",
    "operational_safety",
    "MEDIUM",
    "Kafka broker auto topic creation enabled",
    "Detects production Kafka brokers with automatic topic creation enabled.",
    broker_auto_create_topics_enabled,
    ["kafka", "broker", "governance"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.unclean_leader_election.enabled",
    "resiliency",
    "CRITICAL",
    "Kafka unclean leader election enabled",
    "Detects brokers that allow unclean leader election and potential data loss.",
    broker_unclean_leader_election_enabled,
    ["kafka", "broker", "data-loss"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.rack_awareness.missing",
    "resiliency",
    "HIGH",
    "Kafka broker rack awareness missing",
    "Detects brokers without broker.rack configured.",
    broker_rack_missing,
    ["kafka", "broker", "rack-awareness"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.security.plaintext_listener",
    "operational_safety",
    "HIGH",
    "Kafka plaintext listener configured",
    "Detects Kafka broker listener configuration that includes PLAINTEXT.",
    broker_plaintext_listener_enabled,
    ["kafka", "security", "tls"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.security.authorizer_missing",
    "operational_safety",
    "HIGH",
    "Kafka authorizer missing",
    "Detects brokers without Kafka authorization configured.",
    broker_authorizer_missing,
    ["kafka", "security", "acl"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.security.allow_everyone_if_no_acl",
    "operational_safety",
    "CRITICAL",
    "Kafka allow everyone if no ACL",
    "Detects allow.everyone.if.no.acl.found=true.",
    broker_allow_everyone_if_no_acl,
    ["kafka", "security", "acl"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.controlled_shutdown.disabled",
    "recovery_readiness",
    "MEDIUM",
    "Kafka controlled shutdown disabled",
    "Detects brokers with controlled shutdown disabled.",
    broker_controlled_shutdown_disabled,
    ["kafka", "broker", "maintenance"],
    ["kafka_broker_config"],
)

register(
    "kafka.broker.client_quotas.missing",
    "operational_safety",
    "MEDIUM",
    "Kafka client quotas missing",
    "Detects brokers without producer and consumer quota configuration.",
    broker_client_quotas_missing,
    ["kafka", "quotas", "multi-tenant"],
    ["kafka_broker_config"],
)

register(
    "kafka.topic.replication_factor.low",
    "resiliency",
    "CRITICAL",
    "Kafka topic replication factor too low",
    "Detects Kafka topics with replication factor below production-safe threshold.",
    replication_factor_low,
    ["kafka", "availability", "resiliency"],
)

register(
    "kafka.topic.min_insync_replicas.missing",
    "resiliency",
    "HIGH",
    "Kafka min.insync.replicas missing",
    "Detects Kafka topics without min.insync.replicas.",
    min_insync_replicas_missing,
    ["kafka", "durability", "isr"],
)

register(
    "kafka.topic.min_insync_replicas.unsafe",
    "resiliency",
    "HIGH",
    "Kafka min.insync.replicas unsafe",
    "Detects Kafka topics with unsafe min.insync.replicas.",
    min_insync_replicas_unsafe,
    ["kafka", "durability", "isr"],
)

register(
    "kafka.topic.retention_bytes.missing",
    "storage_sustainability",
    "HIGH",
    "Kafka retention_bytes missing",
    "Detects Kafka topics without retention_bytes.",
    retention_bytes_missing,
    ["kafka", "storage", "capacity"],
)

register(
    "kafka.topic.retention_bytes.large",
    "storage_sustainability",
    "MEDIUM",
    "Kafka retention_bytes very large",
    "Detects Kafka topics with very large retention_bytes settings.",
    retention_bytes_large,
    ["kafka", "storage", "retention"],
)

register(
    "kafka.topic.retention_ms.unbounded",
    "storage_sustainability",
    "HIGH",
    "Kafka retention_ms unbounded",
    "Detects Kafka topics with unbounded retention.",
    retention_ms_unbounded,
    ["kafka", "storage", "retention"],
)

register(
    "kafka.topic.cleanup_policy.missing",
    "storage_sustainability",
    "MEDIUM",
    "Kafka cleanup policy missing",
    "Detects Kafka topics without explicit cleanup policy.",
    cleanup_policy_missing,
    ["kafka", "cleanup", "retention"],
)

register(
    "kafka.topic.max_message_bytes.large",
    "storage_sustainability",
    "HIGH",
    "Kafka max message bytes too large",
    "Detects Kafka topics allowing large messages.",
    max_message_bytes_large,
    ["kafka", "message-size", "latency"],
)

register(
    "kafka.topic.partitions.low",
    "scalability",
    "HIGH",
    "Kafka partition count too low",
    "Detects Kafka topics with low partition count.",
    partitions_low,
    ["kafka", "throughput", "parallelism"],
)

register(
    "kafka.topic.partitions.high",
    "scalability",
    "MEDIUM",
    "Kafka partition count very high",
    "Detects Kafka topics with very high partition count.",
    partitions_high,
    ["kafka", "partitioning", "scalability"],
)

register(
    "kafka.topic.storage_multiplier.high",
    "storage_sustainability",
    "HIGH",
    "Kafka storage multiplier high",
    "Detects Kafka topics with high partition x replication storage multiplier.",
    storage_multiplier_high,
    ["kafka", "storage", "capacity"],
)

register(
    "kafka.topic.storage_multiplier.moderate",
    "storage_sustainability",
    "MEDIUM",
    "Kafka storage multiplier moderate",
    "Detects Kafka topics with moderate partition x replication storage multiplier.",
    storage_multiplier_moderate,
    ["kafka", "storage", "capacity"],
)

register(
    "kafka.topic.segment_bytes.large",
    "storage_sustainability",
    "MEDIUM",
    "Kafka segment bytes large",
    "Detects Kafka topics with large log segment size.",
    segment_bytes_large,
    ["kafka", "segment", "cleanup"],
)

register(
    "kafka.topic.message_size_relative_segment",
    "storage_sustainability",
    "MEDIUM",
    "Kafka message size large relative to segment",
    "Detects Kafka topics where max message size is large relative to segment size.",
    message_size_relative_segment,
    ["kafka", "message-size", "segment"],
)

register(
    "kafka.topic.compacted_without_retention_bytes",
    "storage_sustainability",
    "MEDIUM",
    "Kafka compacted topic without retention_bytes",
    "Detects compacted Kafka topics without retention_bytes limits.",
    compacted_without_retention_bytes,
    ["kafka", "compaction", "storage"],
)

register(
    "kafka.topic.retention_ms.low",
    "storage_sustainability",
    "MEDIUM",
    "Kafka retention period low",
    "Detects Kafka topics with low retention period.",
    retention_ms_low,
    ["kafka", "retention", "recovery"],
)

register(
    "kafka.topic.schema_compatibility.unsafe",
    "operational_safety",
    "HIGH",
    "Kafka topic schema compatibility unsafe",
    "Detects Kafka topics with disabled schema compatibility.",
    schema_compatibility_unsafe,
    ["kafka", "schema", "deployment-safety"],
)

register(
    "kafka.topic.owner.missing",
    "operational_safety",
    "LOW",
    "Kafka topic owner missing",
    "Detects Kafka topics without ownership metadata.",
    topic_owner_missing,
    ["kafka", "governance", "ownership"],
)
