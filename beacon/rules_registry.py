# Add a rules registry loader that loads built-in metadata and optional YAML overrides from BEACON_RULES_METADATA_DIR or package rules/metadata dir.

import os
import glob
import yaml
from typing import Dict, Any

from beacon import rules_metadata as builtin_metadata


_REGISTRY: Dict[str, Dict[str, Any]] = {}


RUNTIME_RULES: Dict[str, Dict[str, Any]] = {
    "kafka.runtime.read_only_mode": {
        "title": "Kafka runtime connector read-only mode",
        "description": "Beacon confirms live Kafka analysis is running without mutation operations.",
        "severity_default": "INFO",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "kafka.runtime.server_config.invalid": {
        "title": "Kafka direct server configuration invalid",
        "description": "Beacon could not safely start live Kafka analysis because direct server configuration was invalid.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Fix the reported direct server configuration values and retry.",
    },
    "kafka.runtime.connection.success": {
        "title": "Kafka runtime connection successful",
        "description": "Beacon connected to Kafka using read-only metadata APIs.",
        "severity_default": "INFO",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "kafka.runtime.connection.failed": {
        "title": "Kafka runtime connection failed",
        "description": "Beacon could not connect to Kafka for live readiness analysis.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check bootstrap server, network access, security protocol, certificates, and firewall rules.",
    },
    "kafka.runtime.analysis_limited": {
        "title": "Kafka runtime analysis limited",
        "description": "Beacon analyzed a subset of topics to keep live diagnostics lightweight.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Increase max topic limit if full cluster coverage is required.",
    },
    "kafka.cluster.broker_count.low": {
        "title": "Kafka cluster broker count low",
        "description": "Low broker count can reduce resiliency and limit safe replication.",
        "severity_default": "HIGH",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Use at least 3 brokers for production Kafka clusters where high availability is required.",
    },
    "kafka.cluster.topic_count.high": {
        "title": "Kafka cluster topic count high",
        "description": "Large topic count can increase controller metadata load and operational complexity.",
        "severity_default": "MEDIUM",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review topic lifecycle, ownership, retention, and retirement opportunities.",
    },
    "kafka.consumer_groups.none_selected": {
        "title": "No Kafka consumer groups selected",
        "description": "Beacon did not find consumer groups to analyze, or no matching group was provided.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Provide a consumer group for targeted lag diagnostics when needed.",
    },
    "kafka.consumer_group.lag.analysis_failed": {
        "title": "Kafka consumer group lag analysis failed",
        "description": "Beacon could not analyze lag for a selected consumer group.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check Kafka permissions for describing consumer groups and listing offsets.",
    },
    "kafka.consumer_group.offsets.missing": {
        "title": "Kafka consumer group offsets missing",
        "description": "Beacon could not calculate lag because no committed offsets were found.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Verify whether the consumer group is active and committing offsets.",
    },
    "kafka.consumer_group.lag.high": {
        "title": "Kafka consumer group lag high",
        "description": "Consumer group lag is high enough to indicate processing delay risk.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check consumer processing latency, downstream dependencies, retries, and recent deployments.",
    },
    "kafka.consumer_group.lag.moderate": {
        "title": "Kafka consumer group lag moderate",
        "description": "Consumer group lag is elevated and should be monitored.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Compare producer and consumer throughput and monitor trend.",
    },
    "kafka.consumer_group.lag.low": {
        "title": "Kafka consumer group lag low",
        "description": "Current offset snapshot does not show severe consumer lag.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Continue monitoring lag trend.",
    },
    "kafka.consumer_group.hot_partition": {
        "title": "Kafka consumer group hot partition",
        "description": "Lag is concentrated on one or more partitions, indicating potential skew.",
        "severity_default": "HIGH",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review partition key distribution and producer key changes.",
    },
    "kafka.consumer_group.decision.partition_skew": {
        "title": "Kafka consumer lag decision: partition skew",
        "description": "Beacon recommends investigating partition skew before scaling consumers.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Investigate hot keys, message distribution, and producer key changes.",
    },
    "kafka.consumer_group.decision.partition_parallelism": {
        "title": "Kafka consumer lag decision: partition parallelism",
        "description": "Beacon recommends reviewing partition parallelism as a lag limiter.",
        "severity_default": "HIGH",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review topic partition count and consumer concurrency.",
    },
    "kafka.consumer_group.decision.consumer_side": {
        "title": "Kafka consumer lag decision: consumer-side investigation",
        "description": "Beacon recommends investigating consumer-side bottlenecks.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check consumer processing time, DB/API latency, retries, poison messages, and deployments.",
    },
    "kafka.consumer_group.decision.no_urgent_action": {
        "title": "Kafka consumer lag decision: no urgent action",
        "description": "Beacon does not see urgent consumer delay from the current offset snapshot.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Continue monitoring lag trend.",
    },
    "kafka.runtime.disk_usage.missing": {
        "title": "Kafka runtime disk usage missing",
        "description": "Runtime snapshot does not include broker disk usage.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Provide broker_disk_usage_percent in runtime input.",
    },
    "kafka.runtime.disk_usage.critical": {
        "title": "Kafka runtime disk usage critical",
        "description": "Broker disk usage is in a critical range.",
        "severity_default": "CRITICAL",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Create immediate headroom and investigate growth drivers.",
    },
    "kafka.runtime.disk_usage.high": {
        "title": "Kafka runtime disk usage high",
        "description": "Broker disk usage is above warning threshold.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Analyze capacity, retention, producer volume, and consumer lag.",
    },
    "kafka.runtime.retention_bytes.missing_under_pressure": {
        "title": "Kafka retention_bytes missing under pressure",
        "description": "retention_bytes is missing while broker disk usage is high.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Set retention_bytes per topic based on disk capacity and throughput.",
    },
    "kafka.runtime.cleanup_policy.missing_under_pressure": {
        "title": "Kafka cleanup policy missing under pressure",
        "description": "Cleanup policy is not explicit while broker disk usage is high.",
        "severity_default": "MEDIUM",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Explicitly configure cleanup policy for production topics.",
    },
    "kafka.runtime.disk_growth.high": {
        "title": "Kafka runtime disk growth high",
        "description": "Broker disk usage increased rapidly over the recent window.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Check recent deployments, producer throughput, payload size, and retention cleanup.",
    },
    "kafka.runtime.producer_rate.increased_under_pressure": {
        "title": "Kafka producer rate increased under disk pressure",
        "description": "Producer rate increased while broker disk usage is high.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Validate whether producer traffic growth is expected.",
    },
    "kafka.runtime.message_size.increased_under_pressure": {
        "title": "Kafka message size increased under disk pressure",
        "description": "Average message size increased while broker disk usage is high.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Review producer payload changes and move large payloads outside Kafka.",
    },
    "kafka.runtime.consumer_lag.increasing_under_pressure": {
        "title": "Kafka consumer lag increasing under disk pressure",
        "description": "Consumer lag is increasing while broker disk usage is high.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check consumer processing latency, downstream calls, retries, and poison messages.",
    },
    "kafka.runtime.under_replicated_partitions": {
        "title": "Kafka under-replicated partitions",
        "description": "Under-replicated partitions indicate broker, disk, network, or replication health issues.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Investigate broker health, disk I/O, network latency, ISR shrink, and leadership distribution.",
    },
    "kafka.runtime.replica_load.high": {
        "title": "Kafka broker replica load high",
        "description": "Replica load per broker is high enough to increase recovery and controller pressure.",
        "severity_default": "HIGH",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review partition strategy, topic count, broker count, and broker expansion needs.",
    },
    "kafka.runtime.decision.capacity_protection": {
        "title": "Kafka runtime decision: capacity protection",
        "description": "Beacon recommends immediate capacity protection action.",
        "severity_default": "CRITICAL",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Create headroom first, then investigate producer volume, message size, and consumer lag.",
    },
    "kafka.runtime.decision.workload_investigation": {
        "title": "Kafka runtime decision: workload investigation",
        "description": "Beacon recommends investigating workload behavior before only expanding disk.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check producer payload changes, consumer latency, retries, and lag by partition.",
    },
    "kafka.runtime.decision.retention_cleanup": {
        "title": "Kafka runtime decision: retention and cleanup",
        "description": "Beacon recommends optimizing storage guardrails before expanding disk.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Configure retention_bytes, cleanup_policy, and topic-level storage limits.",
    },
    "kafka.runtime.decision.disk_expansion": {
        "title": "Kafka runtime decision: disk expansion",
        "description": "Beacon recommends disk or broker capacity expansion.",
        "severity_default": "MEDIUM",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Plan disk expansion or broker capacity increase.",
    },
    "kafka.runtime.decision.monitor_capacity": {
        "title": "Kafka runtime decision: monitor capacity",
        "description": "Beacon does not see urgent disk risk from current runtime signals.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Continue monitoring disk growth, producer rate, message size, consumer lag, and under-replicated partitions.",
    },
}


def _load_from_dir(path: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}

    if not os.path.isdir(path):
        return out

    for p in glob.glob(os.path.join(path, "*.yml")) + glob.glob(
        os.path.join(path, "*.yaml")
    ):
        try:
            with open(p, "r") as f:
                data = yaml.safe_load(f) or {}

            # allow single rule file or list/dict
            if isinstance(data, dict) and "rule_id" in data:
                out[data["rule_id"]] = data
            elif isinstance(data, dict):
                # if file contains multiple rules as mapping
                for k, v in data.items():
                    if isinstance(v, dict):
                        out[k] = v
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "rule_id" in item:
                        out[item["rule_id"]] = item
        except Exception:
            # ignore malformed metadata files
            continue

    return out


def _load_registry() -> Dict[str, Dict[str, Any]]:
    # Prefer package-level YAML metadata as canonical builtins
    registry: Dict[str, Dict[str, Any]] = {}

    package_dir = os.path.join(os.path.dirname(__file__), "rules", "metadata")
    registry.update(_load_from_dir(package_dir))

    # allow overriding/augmentation via env var pointing to a directory of yaml files
    override_dir = os.environ.get("BEACON_RULES_METADATA_DIR")
    if override_dir:
        registry.update(_load_from_dir(override_dir))

    # fallback to builtin python metadata for any missing rules
    builtin = dict(getattr(builtin_metadata, "RULES", {}))
    for k, v in builtin.items():
        if k not in registry:
            registry[k] = v

    for rule_id, metadata in _load_registered_rule_metadata().items():
        if rule_id not in registry:
            registry[rule_id] = metadata

    for rule_id, metadata in RUNTIME_RULES.items():
        if rule_id not in registry:
            registry[rule_id] = {
                "rule_id": rule_id,
                "version": "1.0",
                **metadata,
            }

    return registry


def _load_registered_rule_metadata() -> Dict[str, Dict[str, Any]]:
    try:
        import beacon.rules.iam_registered_rules  # noqa: F401
        import beacon.rules.kafka_registered_rules  # noqa: F401
        import beacon.rules.kubernetes_registered_rules  # noqa: F401
        import beacon.rules.storage_registered_rules  # noqa: F401
        from beacon.engine.registry import registry as engine_registry
    except Exception:
        return {}

    metadata = {}

    for rule in engine_registry.get_all():
        metadata[rule.rule_id] = {
            "rule_id": rule.rule_id,
            "title": rule.title,
            "description": rule.description,
            "severity_default": rule.severity,
            "category": rule.category,
            "author": "beacon.rules",
            "recommendation": "Review the finding recommendation emitted by this rule.",
            "version": "1.0",
            "tags": rule.tags,
        }

    return metadata


def reload():
    global _REGISTRY
    _REGISTRY = _load_registry()


def get(rule_id: str) -> Dict[str, Any]:
    if not _REGISTRY:
        reload()
    return _REGISTRY.get(rule_id)


def list_rules() -> Dict[str, Dict[str, Any]]:
    if not _REGISTRY:
        reload()
    return dict(_REGISTRY)
