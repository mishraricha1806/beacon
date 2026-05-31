from confluent_kafka import TopicPartition, ConsumerGroupTopicPartitions
from confluent_kafka.admin import AdminClient, ConfigResource, ResourceType, OffsetSpec

import beacon.rules.kafka_registered_rules  # noqa: F401
from beacon.diagnose.kafka.server_config import KafkaServerConfig
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kafka_config


def finding(
    severity,
    title,
    impact,
    recommendation,
    file="runtime-kafka",
    rule_id="kafka.runtime.diagnostic",
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


def build_admin_config(
    bootstrap_server,
    security_protocol="PLAINTEXT",
    ca_cert=None,
    client_cert=None,
    client_key=None,
):
    config = {
        "bootstrap.servers": bootstrap_server,
        "security.protocol": security_protocol,
        "socket.timeout.ms": 3000,
        "request.timeout.ms": 3000,
        "metadata.max.age.ms": 30000,
    }

    if security_protocol in ["SSL", "SASL_SSL"]:
        if ca_cert:
            config["ssl.ca.location"] = ca_cert
        if client_cert:
            config["ssl.certificate.location"] = client_cert
        if client_key:
            config["ssl.key.location"] = client_key

    return config


def analyze_kafka_cluster(
    bootstrap_server,
    security_protocol="PLAINTEXT",
    ca_cert=None,
    client_cert=None,
    client_key=None,
    max_topics=50,
    topic=None,
    consumer_group=None,
    max_groups=20,
):
    server_config = KafkaServerConfig(
        bootstrap_server=bootstrap_server,
        security_protocol=security_protocol,
        ca_cert=ca_cert,
        client_cert=client_cert,
        client_key=client_key,
        max_topics=max_topics,
        topic=topic,
        consumer_group=consumer_group,
        max_groups=max_groups,
    )
    findings = []
    findings.append(
        finding(
            "INFO",
            "Beacon Kafka runtime connector is running in read-only diagnostic mode",
            "Beacon will only collect Kafka metadata and configuration signals for analysis.",
            "No produce, consume, offset update, topic mutation, ACL mutation, or infrastructure mutation operation will be performed.",
            rule_id="kafka.runtime.read_only_mode",
            evidence={"mode": "read_only", "mutation_allowed": False},
            confidence="HIGH",
        )
    )

    validation_errors = server_config.validation_errors()

    if validation_errors:
        findings.append(
            finding(
                "ERROR",
                "Kafka direct server configuration is invalid",
                "Beacon cannot safely start live Kafka readiness analysis with invalid connection settings.",
                "Fix the reported direct server configuration values and retry.",
                rule_id="kafka.runtime.server_config.invalid",
                evidence={
                    **server_config.evidence(),
                    "validation_errors": validation_errors,
                },
                confidence="HIGH",
            )
        )
        return findings

    try:
        config = build_admin_config(
            bootstrap_server=bootstrap_server,
            security_protocol=security_protocol,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
        )

        admin_client = AdminClient(config)
        metadata = admin_client.list_topics(timeout=3)

        broker_count = len(metadata.brokers)

        user_topics = [
            topic_name
            for topic_name in metadata.topics.keys()
            if not topic_name.startswith("__")
        ]

        if topic:
            user_topics = [
                topic_name for topic_name in user_topics if topic_name == topic
            ]

        topic_count = len(user_topics)

        findings.append(
            finding(
                "LOW",
                "Kafka cluster connection successful",
                f"Beacon connected successfully. Brokers detected: {broker_count}, user topics detected: {topic_count}.",
                "Beacon used read-only metadata access. No Kafka mutation operation was performed.",
                rule_id="kafka.runtime.connection.success",
                evidence={
                    **server_config.evidence(),
                    "broker_count": broker_count,
                    "topic_count": topic_count,
                },
                confidence="HIGH",
            )
        )

        if broker_count < 3:
            findings.append(
                finding(
                    "HIGH",
                    f"Kafka cluster has only {broker_count} broker(s)",
                    "Low broker count can reduce resiliency and limit safe replication for production workloads.",
                    "Use at least 3 brokers for production Kafka clusters where high availability is required.",
                    rule_id="kafka.cluster.broker_count.low",
                    evidence={
                        "broker_count": broker_count,
                        "expected_minimum": 3,
                    },
                    confidence="HIGH",
                )
            )

        if topic_count > 200:
            findings.append(
                finding(
                    "MEDIUM",
                    f"Kafka cluster has high topic count: {topic_count}",
                    "Large topic count can increase controller metadata load and operational complexity.",
                    "Review topic lifecycle, ownership, retention, and whether old topics can be retired.",
                    rule_id="kafka.cluster.topic_count.high",
                    evidence={
                        "topic_count": topic_count,
                        "review_threshold": 200,
                    },
                    confidence="HIGH",
                )
            )

        findings.extend(
            build_partition_health_findings(
                metadata=metadata,
                topic_names=user_topics,
                broker_count=broker_count,
            )
        )

        selected_topics = user_topics[:max_topics]

        live_topic_models = build_live_topic_models(
            admin_client=admin_client, metadata=metadata, topic_names=selected_topics
        )

        if live_topic_models:
            kafka_config_payload = {"topics": live_topic_models}
            resources = normalize_kafka_config(kafka_config_payload, "runtime-kafka")

            findings.extend(
                evaluate(
                    resources,
                    context={"file": "runtime-kafka"},
                )
            )

        live_broker_models = build_live_broker_models(
            admin_client=admin_client,
            metadata=metadata,
        )

        if live_broker_models:
            kafka_config_payload = {"brokers": live_broker_models}
            resources = normalize_kafka_config(kafka_config_payload, "runtime-kafka")

            findings.extend(
                evaluate(
                    resources,
                    context={"file": "runtime-kafka"},
                )
            )

        if topic_count > max_topics:
            findings.append(
                finding(
                    "LOW",
                    f"Beacon analyzed first {max_topics} topics out of {topic_count}",
                    "Topic analysis was limited to keep runtime diagnostics fast and lightweight.",
                    "Increase --max-topics if deeper cluster-wide analysis is required.",
                    rule_id="kafka.runtime.analysis_limited",
                    evidence={
                        "topic_count": topic_count,
                        "analyzed_topics": max_topics,
                    },
                    confidence="HIGH",
                )
            )

    except Exception as e:
        findings.append(
            finding(
                "ERROR",
                "Kafka cluster connection failed",
                str(e),
                "Check bootstrap server, network access, security protocol, certificates, and firewall rules.",
                rule_id="kafka.runtime.connection.failed",
                evidence={
                    **server_config.evidence(),
                    "error": str(e),
                },
                confidence="HIGH",
            )
        )
        # If we failed to build or connect the AdminClient, return early.
        return findings
    # Only analyze consumer groups when admin client was created successfully
    if "admin_client" in locals() and admin_client is not None:
        findings.extend(
            analyze_consumer_group_lag(
                admin_client=admin_client,
                consumer_group=consumer_group,
                max_groups=max_groups,
            )
        )

    return findings


def build_live_topic_models(admin_client, metadata, topic_names):
    topic_models = []

    config_resources = [
        ConfigResource(ResourceType.TOPIC, topic_name) for topic_name in topic_names
    ]

    topic_configs = {}

    try:
        config_futures = admin_client.describe_configs(config_resources)

        for resource, future in config_futures.items():
            try:
                topic_configs[resource.name] = future.result(timeout=3)
            except Exception:
                topic_configs[resource.name] = {}
    except Exception:
        topic_configs = {}

    for topic_name in topic_names:
        topic_metadata = metadata.topics.get(topic_name)

        if not topic_metadata:
            continue

        partitions = topic_metadata.partitions or {}
        partition_count = len(partitions)

        replication_factor = infer_replication_factor(partitions)

        configs = topic_configs.get(topic_name, {})

        topic_model = {
            "name": topic_name,
            "partitions": partition_count,
            "replication_factor": replication_factor,
            "retention_ms": get_config_int(configs, "retention.ms"),
            "retention_bytes": get_config_int(configs, "retention.bytes"),
            "cleanup_policy": get_config_value(configs, "cleanup.policy"),
            "min_insync_replicas": get_config_int(configs, "min.insync.replicas"),
            "segment_bytes": get_config_int(configs, "segment.bytes"),
            "max_message_bytes": get_config_int(configs, "max.message.bytes"),
            "delete_retention_ms": get_config_int(configs, "delete.retention.ms"),
            "min_cleanable_dirty_ratio": get_config_float(
                configs, "min.cleanable.dirty.ratio"
            ),
        }

        topic_models.append(topic_model)

    return topic_models


def build_live_broker_models(admin_client, metadata):
    broker_ids = [str(broker_id) for broker_id in metadata.brokers.keys()]

    if not broker_ids:
        return []

    config_resources = [
        ConfigResource(ResourceType.BROKER, broker_id) for broker_id in broker_ids
    ]

    broker_configs = {}

    try:
        config_futures = admin_client.describe_configs(config_resources)

        for resource, future in config_futures.items():
            try:
                broker_configs[resource.name] = future.result(timeout=3)
            except Exception:
                broker_configs[resource.name] = {}
    except Exception:
        broker_configs = {}

    broker_models = []

    for broker_id in broker_ids:
        configs = broker_configs.get(broker_id, {})

        broker_models.append(
            {
                "id": broker_id,
                "default_replication_factor": get_config_int(
                    configs, "default.replication.factor"
                ),
                "offsets_topic_replication_factor": get_config_int(
                    configs, "offsets.topic.replication.factor"
                ),
                "transaction_state_log_replication_factor": get_config_int(
                    configs, "transaction.state.log.replication.factor"
                ),
                "log_retention_bytes": get_config_int(configs, "log.retention.bytes"),
                "auto_create_topics_enable": get_config_bool(
                    configs, "auto.create.topics.enable"
                ),
                "broker_rack": get_config_value(configs, "broker.rack"),
                "security_protocol": get_config_value(configs, "security.protocol"),
                "listener_security_protocol_map": get_config_value(
                    configs, "listener.security.protocol.map"
                ),
                "authorizer_class_name": get_config_value(
                    configs, "authorizer.class.name"
                ),
                "allow_everyone_if_no_acl_found": get_config_bool(
                    configs, "allow.everyone.if.no.acl.found"
                ),
                "unclean_leader_election_enable": get_config_bool(
                    configs, "unclean.leader.election.enable"
                ),
                "controlled_shutdown_enable": get_config_bool(
                    configs, "controlled.shutdown.enable"
                ),
                "producer_quota_bytes_per_second": get_config_int(
                    configs, "producer_byte_rate"
                ),
                "consumer_quota_bytes_per_second": get_config_int(
                    configs, "consumer_byte_rate"
                ),
            }
        )

    return broker_models


def analyze_consumer_group_lag(
    admin_client,
    consumer_group=None,
    max_groups=20,
):
    findings = []

    group_ids = discover_consumer_groups(
        admin_client=admin_client,
        consumer_group=consumer_group,
        max_groups=max_groups,
    )

    if not group_ids:
        findings.append(
            finding(
                "LOW",
                "No Kafka consumer groups selected for lag diagnostics",
                "Beacon did not find consumer groups to analyze, or no matching group was provided.",
                "Provide --consumer-group for targeted lag diagnostics.",
                rule_id="kafka.consumer_groups.none_selected",
                evidence={
                    "consumer_group": consumer_group,
                    "max_groups": max_groups,
                },
                confidence="HIGH",
            )
        )
        return findings

    findings.extend(
        describe_consumer_group_stability(
            admin_client=admin_client,
            group_ids=group_ids,
        )
    )

    for group_id in group_ids:
        try:
            lag_summary = calculate_group_lag_admin_only(
                admin_client=admin_client,
                group_id=group_id,
            )

            findings.extend(build_lag_findings(group_id, lag_summary))

        except Exception as e:
            findings.append(
                finding(
                    "ERROR",
                    f"Failed to analyze consumer group lag for '{group_id}'",
                    str(e),
                    "Check Kafka permissions for describing consumer groups and listing offsets.",
                    rule_id="kafka.consumer_group.lag.analysis_failed",
                    evidence={"consumer_group": group_id, "error": str(e)},
                    confidence="HIGH",
                )
            )

    return findings


def discover_consumer_groups(admin_client, consumer_group=None, max_groups=20):
    if consumer_group:
        return [consumer_group]

    try:
        result = admin_client.list_consumer_groups(request_timeout=3).result(timeout=3)

        valid_groups = getattr(result, "valid", []) or []

        group_ids = [
            group.group_id for group in valid_groups if getattr(group, "group_id", None)
        ]

        return group_ids[:max_groups]

    except Exception:
        return []


def calculate_group_lag_admin_only(admin_client, group_id):
    committed_partitions = fetch_committed_offsets(
        admin_client=admin_client,
        group_id=group_id,
    )

    if not committed_partitions:
        return {
            "total_lag": 0,
            "partition_count": 0,
            "max_partition_lag": 0,
            "hot_partitions": [],
            "topics": set(),
            "status": "NO_OFFSETS",
        }

    latest_offsets = fetch_latest_offsets(
        admin_client=admin_client,
        committed_partitions=committed_partitions,
    )

    total_lag = 0
    max_partition_lag = 0
    hot_partitions = []
    topics = set()

    for tp in committed_partitions:
        if tp.topic.startswith("__"):
            continue

        topics.add(tp.topic)

        committed_offset = tp.offset
        latest_offset = latest_offsets.get((tp.topic, tp.partition))

        if committed_offset is None or committed_offset < 0:
            continue

        if latest_offset is None or latest_offset < 0:
            continue

        lag = max(0, latest_offset - committed_offset)

        total_lag += lag
        max_partition_lag = max(max_partition_lag, lag)

        if lag >= 50000:
            hot_partitions.append(
                {
                    "topic": tp.topic,
                    "partition": tp.partition,
                    "lag": lag,
                    "committed_offset": committed_offset,
                    "latest_offset": latest_offset,
                }
            )

    return {
        "total_lag": total_lag,
        "partition_count": len(committed_partitions),
        "max_partition_lag": max_partition_lag,
        "hot_partitions": hot_partitions,
        "topics": topics,
        "status": "OK",
    }


def build_partition_health_findings(metadata, topic_names, broker_count):
    offline_partitions = []
    under_replicated_partitions = []
    under_min_isr_partitions = []
    single_failure_domain_partitions = []
    leader_counts = {}
    total_partitions = 0
    broker_racks = build_broker_rack_map(metadata)

    for topic_name in topic_names:
        topic_metadata = metadata.topics.get(topic_name)

        if not topic_metadata:
            continue

        for partition_id, partition_metadata in (
            topic_metadata.partitions or {}
        ).items():
            total_partitions += 1
            leader = getattr(partition_metadata, "leader", None)
            replicas = list(getattr(partition_metadata, "replicas", []) or [])
            isrs = list(getattr(partition_metadata, "isrs", []) or [])
            replica_racks = [
                broker_racks.get(str(replica))
                for replica in replicas
                if broker_racks.get(str(replica))
            ]

            if leader is None or leader < 0:
                offline_partitions.append(
                    {
                        "topic": topic_name,
                        "partition": partition_id,
                        "leader": leader,
                    }
                )
            else:
                leader_counts[leader] = leader_counts.get(leader, 0) + 1

            if replicas and isrs and len(isrs) < len(replicas):
                under_replicated_partitions.append(
                    {
                        "topic": topic_name,
                        "partition": partition_id,
                        "replicas": replicas,
                        "isr": isrs,
                    }
                )

            if replicas and len(isrs) <= max(1, len(replicas) - 2):
                under_min_isr_partitions.append(
                    {
                        "topic": topic_name,
                        "partition": partition_id,
                        "replicas": replicas,
                        "isr": isrs,
                    }
                )

            if (
                len(replicas) > 1
                and len(replica_racks) == len(replicas)
                and len(set(replica_racks)) < 2
            ):
                single_failure_domain_partitions.append(
                    {
                        "topic": topic_name,
                        "partition": partition_id,
                        "replicas": replicas,
                        "racks": replica_racks,
                    }
                )

    findings = []

    if offline_partitions:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {len(offline_partitions)} offline partition(s)",
                "Offline partitions are unavailable and indicate active production impact.",
                "Restore affected brokers, inspect partition leadership, and validate replica recovery.",
                rule_id="kafka.cluster.offline_partitions",
                category="resiliency",
                evidence={
                    "offline_partitions": offline_partitions[:10],
                    "offline_partition_count": len(offline_partitions),
                },
                confidence="HIGH",
            )
        )

    if under_replicated_partitions:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {len(under_replicated_partitions)} under-replicated partition(s)",
                "Under-replicated partitions weaken failover safety and can precede unavailability.",
                "Investigate slow replicas, broker health, disk I/O, network latency, and ISR shrink.",
                rule_id="kafka.cluster.under_replicated_partitions",
                category="resiliency",
                evidence={
                    "under_replicated_partitions": under_replicated_partitions[:10],
                    "under_replicated_partition_count": len(
                        under_replicated_partitions
                    ),
                },
                confidence="HIGH",
            )
        )

    if under_min_isr_partitions:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {len(under_min_isr_partitions)} partition(s) below safe ISR",
                "Partitions below safe ISR can reject durable writes or lose fault tolerance.",
                "Restore ISR health before increasing producer pressure or rolling more brokers.",
                rule_id="kafka.cluster.under_min_isr_partitions",
                category="resiliency",
                evidence={
                    "under_min_isr_partitions": under_min_isr_partitions[:10],
                    "under_min_isr_partition_count": len(under_min_isr_partitions),
                },
                confidence="HIGH",
            )
        )

    if single_failure_domain_partitions:
        findings.append(
            finding(
                "CRITICAL",
                f"Kafka has {len(single_failure_domain_partitions)} partition(s) with replicas in one rack/AZ",
                "A single rack or availability-zone failure can remove multiple replicas for the same partition.",
                "Reassign replicas so each partition spans at least two failure domains, preferably all available AZs for RF=3.",
                rule_id="kafka.cluster.replica_placement.single_failure_domain",
                category="resiliency",
                evidence={
                    "risky_partitions": single_failure_domain_partitions[:10],
                    "risky_partition_count": len(single_failure_domain_partitions),
                },
                confidence="HIGH",
            )
        )

    if total_partitions and broker_count and leader_counts:
        average_leaders = total_partitions / broker_count
        max_leader_count = max(leader_counts.values())
        leader_imbalance_percent = (
            ((max_leader_count - average_leaders) / average_leaders) * 100
            if average_leaders
            else 0
        )

        if leader_imbalance_percent >= 50:
            findings.append(
                finding(
                    "HIGH",
                    "Kafka partition leadership is imbalanced across brokers",
                    "Leader imbalance can overload a subset of brokers and create uneven request latency.",
                    "Review preferred leader election safety, broker load, and partition distribution.",
                    rule_id="kafka.cluster.leader_imbalance.high",
                    category="scalability",
                    evidence={
                        "leader_counts": leader_counts,
                        "total_partitions": total_partitions,
                        "broker_count": broker_count,
                        "leader_imbalance_percent": round(leader_imbalance_percent, 2),
                    },
                    confidence="HIGH",
                )
            )

    return findings


def build_broker_rack_map(metadata):
    broker_racks = {}

    for broker_id, broker in (getattr(metadata, "brokers", {}) or {}).items():
        rack = (
            getattr(broker, "rack", None)
            or getattr(broker, "broker_rack", None)
            or getattr(broker, "az", None)
            or getattr(broker, "zone", None)
        )

        if rack:
            broker_racks[str(broker_id)] = str(rack)

    return broker_racks


def fetch_committed_offsets(admin_client, group_id):
    request = ConsumerGroupTopicPartitions(group_id)

    futures = admin_client.list_consumer_group_offsets([request], request_timeout=3)

    future = futures.get(group_id)

    if future is None:
        return []

    result = future.result(timeout=3)

    topic_partitions = getattr(result, "topic_partitions", None)

    if topic_partitions is None:
        return []

    return [tp for tp in topic_partitions if tp.topic and not tp.topic.startswith("__")]


def fetch_latest_offsets(admin_client, committed_partitions):
    offset_requests = {}

    for tp in committed_partitions:
        if tp.topic.startswith("__"):
            continue

        offset_requests[TopicPartition(tp.topic, tp.partition)] = OffsetSpec.latest()

    if not offset_requests:
        return {}

    futures = admin_client.list_offsets(offset_requests, request_timeout=3)

    latest_offsets = {}

    for topic_partition, future in futures.items():
        try:
            result = future.result(timeout=3)
            latest_offsets[(topic_partition.topic, topic_partition.partition)] = (
                result.offset
            )
        except Exception:
            continue

    return latest_offsets


def build_lag_findings(group_id, lag_summary):
    findings = []

    total_lag = lag_summary["total_lag"]
    max_partition_lag = lag_summary["max_partition_lag"]
    hot_partitions = lag_summary["hot_partitions"]
    partition_count = lag_summary["partition_count"]
    status = lag_summary["status"]

    if status == "NO_OFFSETS":
        findings.append(
            finding(
                "LOW",
                f"No committed offsets found for consumer group '{group_id}'",
                "Beacon could not calculate lag because the group has no committed offsets.",
                "Verify whether the consumer group is active and committing offsets.",
                rule_id="kafka.consumer_group.offsets.missing",
                evidence={"consumer_group": group_id, "status": status},
                confidence="HIGH",
            )
        )
        return findings

    if total_lag >= 100000:
        findings.append(
            finding(
                "HIGH",
                f"High Kafka consumer lag detected for group '{group_id}'",
                f"Total lag is approximately {total_lag} across {partition_count} partitions.",
                "Check consumer processing latency, downstream dependency slowness, retry loops, rebalance frequency, and producer throughput.",
                rule_id="kafka.consumer_group.lag.high",
                evidence={
                    "consumer_group": group_id,
                    "total_lag": total_lag,
                    "partition_count": partition_count,
                    "max_partition_lag": max_partition_lag,
                },
                confidence="HIGH",
            )
        )

    elif total_lag >= 10000:
        findings.append(
            finding(
                "MEDIUM",
                f"Moderate Kafka consumer lag detected for group '{group_id}'",
                f"Total lag is approximately {total_lag} across {partition_count} partitions.",
                "Monitor lag trend and compare consumer throughput against producer rate.",
                rule_id="kafka.consumer_group.lag.moderate",
                evidence={
                    "consumer_group": group_id,
                    "total_lag": total_lag,
                    "partition_count": partition_count,
                    "max_partition_lag": max_partition_lag,
                },
                confidence="HIGH",
            )
        )

    else:
        findings.append(
            finding(
                "LOW",
                f"Kafka consumer group '{group_id}' lag is currently low",
                f"Total lag is approximately {total_lag} across {partition_count} partitions.",
                "No major lag pressure detected from current offset snapshot.",
                rule_id="kafka.consumer_group.lag.low",
                evidence={
                    "consumer_group": group_id,
                    "total_lag": total_lag,
                    "partition_count": partition_count,
                    "max_partition_lag": max_partition_lag,
                },
                confidence="HIGH",
            )
        )

    if hot_partitions:
        top_hot = sorted(hot_partitions, key=lambda item: item["lag"], reverse=True)[:5]

        hot_summary = ", ".join(
            [
                f"{item['topic']}[{item['partition']}]=lag:{item['lag']}"
                for item in top_hot
            ]
        )

        findings.append(
            finding(
                "HIGH",
                f"Potential hot partition behavior detected for group '{group_id}'",
                f"Max partition lag is {max_partition_lag}. Top hot partitions: {hot_summary}.",
                "Review partition key distribution, producer key changes, skewed events, and whether consumer parallelism matches partition distribution.",
                rule_id="kafka.consumer_group.hot_partition",
                evidence={
                    "consumer_group": group_id,
                    "max_partition_lag": max_partition_lag,
                    "hot_partitions": top_hot,
                    "hot_partition_threshold": 50000,
                },
                confidence="HIGH",
            )
        )

    findings.append(build_lag_decision_finding(group_id, lag_summary))

    return findings


def build_consumer_group_stability_findings(group_id, group_description):
    state = str(getattr(group_description, "state", "") or "").upper()
    members = getattr(group_description, "members", []) or []
    member_count = len(members)

    findings = []

    if state in {"REBALANCING", "PREPARING_REBALANCE", "COMPLETING_REBALANCE"}:
        findings.append(
            finding(
                "HIGH",
                f"Kafka consumer group '{group_id}' is unstable: {state}",
                "Consumer group rebalancing can pause consumption and increase lag during incidents.",
                "Inspect member churn, deployment rollouts, heartbeat/session timeouts, max.poll settings, and consumer crashes.",
                rule_id="kafka.consumer_group.rebalancing",
                evidence={
                    "consumer_group": group_id,
                    "state": state,
                    "member_count": member_count,
                },
                confidence="HIGH",
            )
        )
    elif state == "EMPTY":
        findings.append(
            finding(
                "MEDIUM",
                f"Kafka consumer group '{group_id}' has no active members",
                "An empty consumer group cannot process backlog until consumers return.",
                "Check consumer deployment health, scaling, and recent rollouts.",
                rule_id="kafka.consumer_group.empty",
                evidence={
                    "consumer_group": group_id,
                    "state": state,
                    "member_count": member_count,
                },
                confidence="HIGH",
            )
        )

    return findings


def describe_consumer_group_stability(admin_client, group_ids):
    if not group_ids or not hasattr(admin_client, "describe_consumer_groups"):
        return []

    findings = []

    try:
        futures = admin_client.describe_consumer_groups(group_ids, request_timeout=3)
    except TypeError:
        try:
            futures = admin_client.describe_consumer_groups(group_ids)
        except Exception:
            return []
    except Exception:
        return []

    for group_id, future in (futures or {}).items():
        try:
            description = future.result(timeout=3)
        except Exception:
            continue

        findings.extend(build_consumer_group_stability_findings(group_id, description))

    return findings


def build_lag_decision_finding(group_id, lag_summary):
    total_lag = lag_summary["total_lag"]
    hot_partitions = lag_summary["hot_partitions"]
    partition_count = lag_summary["partition_count"]

    if total_lag >= 100000 and hot_partitions:
        return finding(
            "HIGH",
            f"Decision: Consumer delay for '{group_id}' may be caused by partition skew",
            "Lag is high and concentrated on one or more partitions, which usually means adding more consumers alone may not solve the issue.",
            "Investigate message key distribution, hot keys, uneven partition assignment, and recent producer key changes.",
            rule_id="kafka.consumer_group.decision.partition_skew",
            evidence={
                "consumer_group": group_id,
                "total_lag": total_lag,
                "partition_count": partition_count,
                "hot_partitions": hot_partitions,
            },
            confidence="HIGH",
        )

    if total_lag >= 100000 and partition_count <= 3:
        return finding(
            "HIGH",
            f"Decision: Consumer delay for '{group_id}' may be limited by partition parallelism",
            "Lag is high while partition count is low, which can cap consumer parallelism.",
            "Review topic partition count and consumer concurrency. Increase partitions only after validating ordering and keying impact.",
            rule_id="kafka.consumer_group.decision.partition_parallelism",
            evidence={
                "consumer_group": group_id,
                "total_lag": total_lag,
                "partition_count": partition_count,
            },
            confidence="HIGH",
        )

    if total_lag >= 100000:
        return finding(
            "HIGH",
            f"Decision: Consumer delay for '{group_id}' needs consumer-side investigation",
            "Lag is high but current offset snapshot alone does not prove Kafka broker failure.",
            "Check consumer processing time, DB/API latency, thread pools, retries, poison messages, and recent application deployments.",
            rule_id="kafka.consumer_group.decision.consumer_side",
            evidence={
                "consumer_group": group_id,
                "total_lag": total_lag,
                "partition_count": partition_count,
            },
            confidence="MEDIUM",
        )

    return finding(
        "LOW",
        f"Decision: No urgent consumer delay action required for '{group_id}'",
        "Current offset snapshot does not show severe consumer lag.",
        "Continue monitoring lag trend and correlate with producer rate and application logs.",
        rule_id="kafka.consumer_group.decision.no_urgent_action",
        evidence={
            "consumer_group": group_id,
            "total_lag": total_lag,
            "partition_count": partition_count,
        },
        confidence="HIGH",
    )


def infer_replication_factor(partitions):
    replication_factors = []

    for _, partition_metadata in partitions.items():
        replicas = getattr(partition_metadata, "replicas", None)

        if replicas is not None:
            replication_factors.append(len(replicas))

    if not replication_factors:
        return None

    return min(replication_factors)


def get_config_value(configs, key):
    config_entry = configs.get(key)

    if config_entry is None:
        return None

    return config_entry.value


def get_config_int(configs, key):
    value = get_config_value(configs, key)

    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def get_config_float(configs, key):
    value = get_config_value(configs, key)

    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def get_config_bool(configs, key):
    value = get_config_value(configs, key)

    if value is None:
        return None

    return str(value).lower() == "true"
