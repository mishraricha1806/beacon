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
    "kafka.runtime.access.invalid": {
        "title": "Kafka access config invalid",
        "description": "Kafka access profile configuration is invalid.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Fix Kafka access profile validation errors and retry.",
    },
    "kafka.runtime.access.cluster_profile.missing": {
        "title": "Kafka cluster access profile missing",
        "description": "No access profile can perform Kafka cluster discovery.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Add a cluster or all-scope profile with list_topics capability.",
    },
    "kafka.runtime.access.cluster_profile.loaded": {
        "title": "Kafka cluster access profile loaded",
        "description": "Beacon selected a read-only profile for Kafka cluster discovery.",
        "severity_default": "INFO",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "kafka.runtime.access.topic_profile.loaded": {
        "title": "Kafka topic access profile loaded",
        "description": "Beacon selected a read-only profile for Kafka topic diagnostics.",
        "severity_default": "INFO",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "kafka.runtime.access.topic_profile.missing": {
        "title": "Kafka topic access profile missing",
        "description": "Beacon discovered a topic without a matching scoped topic access profile.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Add a topic or all-scope profile if this topic requires separate credentials.",
    },
    "kafka.runtime.access.consumer_group_profile.loaded": {
        "title": "Kafka consumer group access profile loaded",
        "description": "Beacon selected a read-only profile for Kafka consumer group diagnostics.",
        "severity_default": "INFO",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "kafka.runtime.access.consumer_group_profile.missing": {
        "title": "Kafka consumer group access profile missing",
        "description": "Beacon did not find a matching consumer group access profile.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Add a consumer_group or all-scope profile if this group requires separate credentials.",
    },
    "kafka.runtime.access.auth.plaintext": {
        "title": "Kafka access profile uses plaintext",
        "description": "A Kafka access profile uses plaintext transport.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Use SSL, mTLS, or SASL over SSL for production Kafka access profiles.",
    },
    "kafka.runtime.access.auth.sasl_without_ssl": {
        "title": "Kafka SASL access profile without SSL",
        "description": "A Kafka access profile uses SASL without SSL.",
        "severity_default": "CRITICAL",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Use SASL_SSL for production Kafka access profiles.",
    },
    "kafka.runtime.access.auth.sasl_plain": {
        "title": "Kafka access profile uses SASL/PLAIN",
        "description": "A Kafka access profile uses SASL/PLAIN.",
        "severity_default": "MEDIUM",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Prefer SCRAM, OAUTHBEARER, or mTLS where available; ensure SASL/PLAIN only runs over SSL.",
    },
    "kafka.runtime.access.auth.scram_sha256": {
        "title": "Kafka access profile uses SCRAM-SHA-256",
        "description": "A Kafka access profile uses SCRAM-SHA-256.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Prefer SCRAM-SHA-512 when supported by the Kafka platform.",
    },
    "kafka.runtime.access.scope.broad": {
        "title": "Kafka access profile scope broad",
        "description": "A Kafka access profile has broad all-cluster scope.",
        "severity_default": "MEDIUM",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Prefer cluster, topic, or consumer_group scoped profiles with explicit capabilities.",
    },
    "kafka.runtime.access.scope.topic_unbounded": {
        "title": "Kafka topic access profile unbounded",
        "description": "A topic-scoped Kafka access profile has no topic patterns.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Set explicit topic names or patterns for topic-scoped profiles.",
    },
    "kafka.runtime.access.scope.consumer_group_unbounded": {
        "title": "Kafka consumer group access profile unbounded",
        "description": "A consumer-group-scoped Kafka access profile has no group patterns.",
        "severity_default": "MEDIUM",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Set explicit consumer group names or patterns for consumer-group-scoped profiles.",
    },
    "kafka.runtime.access.cert.expired": {
        "title": "Kafka access profile certificate expired",
        "description": "A Kafka access profile certificate is expired.",
        "severity_default": "CRITICAL",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Rotate the expired Kafka certificate immediately.",
    },
    "kafka.runtime.access.cert.expiring_soon": {
        "title": "Kafka access profile certificate expiring soon",
        "description": "A Kafka access profile certificate expires soon.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Rotate the Kafka certificate before the expiry window closes.",
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
    "kafka.cluster.offline_partitions": {
        "title": "Kafka cluster offline partitions",
        "description": "One or more Kafka partitions have no valid leader and are unavailable.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Restore affected brokers, inspect leadership, and validate replica recovery.",
    },
    "kafka.cluster.under_replicated_partitions": {
        "title": "Kafka cluster under-replicated partitions",
        "description": "One or more Kafka partitions have fewer in-sync replicas than assigned replicas.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Investigate slow replicas, broker health, disk I/O, network latency, and ISR shrink.",
    },
    "kafka.cluster.under_min_isr_partitions": {
        "title": "Kafka cluster partitions below safe ISR",
        "description": "One or more Kafka partitions are below a safe ISR threshold.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Restore ISR health before increasing producer pressure or rolling more brokers.",
    },
    "kafka.cluster.leader_imbalance.high": {
        "title": "Kafka cluster leader imbalance high",
        "description": "Partition leadership is concentrated on too few brokers.",
        "severity_default": "HIGH",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review preferred leader election safety, broker load, and partition distribution.",
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
    "kafka.consumer_group.rebalancing": {
        "title": "Kafka consumer group rebalancing",
        "description": "Consumer group state indicates active rebalance instability.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect member churn, deployment rollouts, heartbeat/session timeouts, max.poll settings, and consumer crashes.",
    },
    "kafka.consumer_group.empty": {
        "title": "Kafka consumer group empty",
        "description": "Consumer group has no active members.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check consumer deployment health, scaling, and recent rollouts.",
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
    "kafka.runtime.broker_disk_skew.critical": {
        "title": "Kafka broker disk skew critical",
        "description": "One Kafka broker is critically full even if aggregate cluster disk may look acceptable.",
        "severity_default": "CRITICAL",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Create broker-specific headroom, inspect partition placement, and move or reassign hot partitions.",
    },
    "kafka.runtime.broker_disk_skew.high": {
        "title": "Kafka broker disk usage skew high",
        "description": "Kafka broker disk usage is uneven across brokers.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.runtime",
        "recommendation": "Review partition placement, topic retention, leader distribution, and reassignment needs.",
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
    "kafka.runtime.offline_partitions": {
        "title": "Kafka offline partitions",
        "description": "Runtime signals indicate offline partitions.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Identify affected brokers and partitions, restore broker health, and validate replica recovery.",
    },
    "kafka.runtime.under_min_isr_partitions": {
        "title": "Kafka partitions below min ISR",
        "description": "Runtime signals indicate partitions below min ISR.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Restore ISR health, inspect slow replicas, disk I/O, network latency, and broker placement.",
    },
    "kafka.runtime.leader_imbalance.high": {
        "title": "Kafka runtime leader imbalance high",
        "description": "Runtime signals indicate imbalanced partition leadership.",
        "severity_default": "HIGH",
        "category": "scalability",
        "author": "beacon.runtime",
        "recommendation": "Review partition leadership, preferred leader election safety, and broker load distribution.",
    },
    "kafka.runtime.controller_count.invalid": {
        "title": "Kafka active controller count invalid",
        "description": "Kafka runtime signals show zero or multiple active controllers.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Investigate controller election, broker quorum health, ZooKeeper/KRaft health, and recent broker restarts.",
    },
    "kafka.runtime.controller_churn.high": {
        "title": "Kafka controller churn high",
        "description": "Kafka controller changed repeatedly over a short window.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect broker churn, controller logs, quorum health, GC pauses, and network instability.",
    },
    "kafka.runtime.partition_reassignment.active": {
        "title": "Kafka partition reassignment active",
        "description": "Kafka has active partition reassignments.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Validate reassignment throttle, broker headroom, and incident safety before continuing.",
    },
    "kafka.runtime.replication_fetcher_lag.high": {
        "title": "Kafka replication fetcher lag high",
        "description": "Kafka replica fetcher lag is elevated.",
        "severity_default": "HIGH",
        "category": "resiliency",
        "author": "beacon.runtime",
        "recommendation": "Inspect follower broker disk, network, inter-broker throttles, and replication fetcher health.",
    },
    "kafka.runtime.rebalance_storm": {
        "title": "Kafka rebalance storm",
        "description": "Consumer group rebalance frequency is high.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect deployment churn, heartbeat/session timeouts, max.poll settings, and consumer crashes.",
    },
    "kafka.runtime.consumer_group.unstable": {
        "title": "Kafka consumer group unstable",
        "description": "Consumer group state indicates instability.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Review member churn, consumer logs, polling behavior, session timeout, and recent deploys.",
    },
    "kafka.runtime.consumer_group.no_active_members": {
        "title": "Kafka consumer group no active members",
        "description": "Consumer group has no active members while lag is increasing.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Restore consumer deployment health, check scaling targets, and verify group membership.",
    },
    "kafka.runtime.consumer_group.member_shortfall": {
        "title": "Kafka consumer group member shortfall",
        "description": "Consumer group has fewer active members than expected.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check consumer pod/process health, autoscaling, deployment rollout, and assignment balance.",
    },
    "kafka.runtime.producer_error_rate.high": {
        "title": "Kafka producer error rate high",
        "description": "Producer error rate is elevated.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect producer error classes, broker request errors, throttling, auth, and recent producer deployments.",
    },
    "kafka.runtime.request_latency.high": {
        "title": "Kafka request latency high",
        "description": "Kafka request p95 latency is high.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect broker CPU, disk I/O, network, request queues, throttling, and hot partitions.",
    },
    "kafka.runtime.request_queue_saturation.high": {
        "title": "Kafka request queue saturation high",
        "description": "Kafka request queue utilization is high.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect broker CPU, network processors, disk I/O, request handlers, and hot clients.",
    },
    "kafka.runtime.network_saturation.high": {
        "title": "Kafka network saturation high",
        "description": "Kafka broker network I/O utilization is high.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Review broker network throughput, cross-AZ replication, client traffic, and compression settings.",
    },
    "kafka.runtime.producer_throttle.high": {
        "title": "Kafka producer throttle high",
        "description": "Kafka producer throttle time is elevated.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Review producer quotas, broker load, client traffic spikes, and whether throttling is expected.",
    },
    "kafka.runtime.fetch_throttle.high": {
        "title": "Kafka fetch throttle high",
        "description": "Kafka consumer fetch throttle time is elevated.",
        "severity_default": "MEDIUM",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Review consumer quotas, broker load, client traffic spikes, and whether throttling is expected.",
    },
    "kafka.runtime.schema_registry.unavailable": {
        "title": "Kafka Schema Registry unavailable",
        "description": "Kafka Schema Registry is unavailable.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Restore Schema Registry health and verify producer and consumer fallback behavior.",
    },
    "kafka.runtime.schema_incompatible_changes": {
        "title": "Kafka incompatible schema changes",
        "description": "Kafka runtime signals show incompatible schema changes.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Review schema compatibility mode, producer deployment diff, and affected consumers before rollout.",
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
    "helm.render.unavailable": {
        "title": "Helm renderer unavailable",
        "description": "Beacon found a Helm chart but could not render it because the Helm CLI is unavailable.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.scanner",
        "recommendation": "Install the helm CLI or provide rendered Kubernetes manifests for scanning.",
    },
    "helm.render.failed": {
        "title": "Helm chart render failed",
        "description": "Beacon found a Helm chart but helm template failed.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.scanner",
        "recommendation": "Run helm template locally, fix chart rendering errors, and retry Beacon.",
    },
    "k8s.runtime.read_only_mode": {
        "title": "Kubernetes runtime connector read-only mode",
        "description": "Beacon confirms live Kubernetes analysis is running without mutation operations.",
        "severity_default": "INFO",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "k8s.runtime.kubectl.unavailable": {
        "title": "kubectl unavailable",
        "description": "Beacon cannot collect live Kubernetes runtime signals because kubectl is unavailable.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Install kubectl or provide a Kubernetes runtime snapshot YAML.",
    },
    "k8s.runtime.collection.failed": {
        "title": "Kubernetes runtime collection failed",
        "description": "Beacon could not collect Kubernetes runtime status.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check kubectl access, kubeconfig, context, namespace, and cluster API availability.",
    },
    "k8s.runtime.collection.success": {
        "title": "Kubernetes runtime collection successful",
        "description": "Beacon collected Kubernetes runtime status using read-only kubectl get commands.",
        "severity_default": "LOW",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "prometheus.runtime.read_only_mode": {
        "title": "Prometheus connector read-only mode",
        "description": "Beacon confirms Prometheus analysis is running through read-only query APIs.",
        "severity_default": "INFO",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "prometheus.config.url.missing": {
        "title": "Prometheus URL missing",
        "description": "Beacon cannot query Prometheus without a base URL.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Set prometheus.url in the collector config.",
    },
    "prometheus.query.failed": {
        "title": "Prometheus query failed",
        "description": "Beacon could not collect one or more Prometheus runtime signals.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Check the query, Prometheus URL, network access, and metric availability.",
    },
    "schema_registry.runtime.read_only_mode": {
        "title": "Schema Registry connector read-only mode",
        "description": "Beacon confirms Schema Registry analysis is using read-only metadata APIs.",
        "severity_default": "INFO",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "schema_registry.config.url.missing": {
        "title": "Schema Registry URL missing",
        "description": "Beacon cannot query Schema Registry without a base URL.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Set schema_registry.url in the collector config.",
    },
    "schema_registry.query.failed": {
        "title": "Schema Registry query failed",
        "description": "Beacon could not collect one or more Schema Registry signals.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Check the Schema Registry URL, credentials, network access, and API permissions.",
    },
    "schema_registry.compatibility.global_unsafe": {
        "title": "Schema Registry global compatibility unsafe",
        "description": "Global Schema Registry compatibility allows unsafe schema evolution.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Use BACKWARD, FULL, or an approved compatibility mode for production event schemas.",
    },
    "schema_registry.subject.compatibility.unsafe": {
        "title": "Schema Registry subject compatibility unsafe",
        "description": "A schema subject allows unsafe schema evolution.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Use BACKWARD, FULL, or an approved subject-level compatibility mode.",
    },
    "schema_registry.topic.subject.missing": {
        "title": "Kafka topic missing expected schema subject",
        "description": "A Kafka topic is missing one or more expected Schema Registry subjects.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Register and enforce expected key/value subjects for production topics.",
    },
    "schema_registry.subject.latest_schema.missing": {
        "title": "Schema Registry latest schema body missing",
        "description": "A schema subject latest version has no schema body available.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Check Schema Registry subject health and permissions.",
    },
    "schema_registry.subject.schema_type.missing": {
        "title": "Schema Registry schema type missing",
        "description": "A schema subject does not expose an explicit schema type.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Set or verify schema type where the platform supports it.",
    },
    "schema_registry.subject.latest_version.unavailable": {
        "title": "Schema Registry latest version unavailable",
        "description": "Beacon could not inspect the latest schema version for a subject.",
        "severity_default": "ERROR",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Check Schema Registry permissions, subject existence, and API health.",
    },
    "kafka.runtime.client_quotas.configured": {
        "title": "Kafka client quotas configured",
        "description": "Beacon detected producer and consumer byte-rate quota settings.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Validate quota values against tenant isolation and peak traffic requirements.",
    },
    "kafka.runtime.client_quotas.missing": {
        "title": "Kafka client quotas missing",
        "description": "Kafka broker client quotas are not fully configured.",
        "severity_default": "MEDIUM",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Configure producer and consumer byte-rate quotas or document equivalent platform-level traffic controls.",
    },
    "kafka.runtime.acl.analysis_unavailable": {
        "title": "Kafka ACL analysis unavailable",
        "description": "The active Kafka client does not expose a read-only ACL describe API.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Provide ACL exports or use a Kafka client/platform that supports describe_acls for authorization posture checks.",
    },
    "kafka.runtime.acl.collection_failed": {
        "title": "Kafka ACL collection failed",
        "description": "Beacon could not inspect Kafka ACLs through the read-only Admin API.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Check Describe ACL permissions or provide an ACL export for offline analysis.",
    },
    "kafka.runtime.acl.none_found": {
        "title": "Kafka ACL list empty",
        "description": "Kafka returned no ACL bindings for read-only inspection.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Verify authorizer configuration and document equivalent platform authorization controls.",
    },
    "kafka.runtime.acl.broad_allow": {
        "title": "Kafka ACL broad allow",
        "description": "Kafka ACLs include broad wildcard or all-operation allow permissions.",
        "severity_default": "HIGH",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Replace wildcard or all-operation ACLs with scoped topic, group, and transactional-id permissions.",
    },
    "kafka.runtime.acl.posture_inspected": {
        "title": "Kafka ACL posture inspected",
        "description": "Beacon inspected Kafka ACL metadata and did not detect broad allow patterns.",
        "severity_default": "LOW",
        "category": "operational_safety",
        "author": "beacon.runtime",
        "recommendation": "Continue enforcing least privilege and review ACL changes during production readiness checks.",
    },
    "kafka.consumer_group.member_churn.high": {
        "title": "Kafka consumer group member churn high",
        "description": "Consumer group membership changed repeatedly during a sampling window.",
        "severity_default": "HIGH",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Inspect rolling deployments, session timeout, heartbeat interval, max.poll.interval.ms, and consumer crashes.",
    },
    "opentelemetry.runtime.read_only_mode": {
        "title": "OpenTelemetry connector read-only mode",
        "description": "Beacon confirms OpenTelemetry analysis is reading exported telemetry without mutation.",
        "severity_default": "INFO",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "No action required.",
    },
    "opentelemetry.runtime.signals.missing": {
        "title": "OpenTelemetry runtime signals missing",
        "description": "Beacon could not derive runtime resources from the provided OpenTelemetry input.",
        "severity_default": "ERROR",
        "category": "runtime_stability",
        "author": "beacon.runtime",
        "recommendation": "Provide spans or metrics with service names, durations, status, and relevant runtime signal values.",
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
        import beacon.rules.api_runtime_registered_rules  # noqa: F401
        import beacon.rules.cicd_registered_rules  # noqa: F401
        import beacon.rules.cloud_registered_rules  # noqa: F401
        import beacon.rules.database_runtime_registered_rules  # noqa: F401
        import beacon.rules.flow_registered_rules  # noqa: F401
        import beacon.rules.kafka_registered_rules  # noqa: F401
        import beacon.rules.kubernetes_registered_rules  # noqa: F401
        import beacon.rules.kubernetes_runtime_registered_rules  # noqa: F401
        import beacon.rules.storage_runtime_registered_rules  # noqa: F401
        import beacon.rules.storage_registered_rules  # noqa: F401
        import beacon.rules.topology_registered_rules  # noqa: F401
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
