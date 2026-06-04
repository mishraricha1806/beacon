import logging
import time

from confluent_kafka import TopicPartition, ConsumerGroupTopicPartitions
from confluent_kafka.admin import (
    AdminClient,
    ConfigResource,
    ResourceType,
    OffsetSpec,
)

import beacon.rules.kafka_registered_rules  # noqa: F401
from beacon.diagnose.kafka.access_config import (
    admin_config_from_profile,
    load_kafka_access_config,
)
from beacon.diagnose.kafka.server_config import (
    KafkaServerConfig,
    normalize_bootstrap_servers,
)
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kafka_config


LOGGER = logging.getLogger(__name__)


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
    bootstrap_servers = normalize_bootstrap_servers(bootstrap_server)
    config = {
        "bootstrap.servers": bootstrap_servers,
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


def access_profile_finding(rule_id, severity, title, impact, recommendation, evidence):
    return finding(
        severity,
        title,
        impact,
        recommendation,
        rule_id=rule_id,
        category="operational_safety",
        evidence=evidence,
        confidence="HIGH",
    )


def connection_evidence(server_config, profile=None):
    evidence = server_config.evidence()

    if profile:
        evidence.update(
            {
                "access_profile": profile.evidence(),
                "security_protocol": None,
                "ca_cert_configured": bool(profile.auth.values.get("ca_cert")),
                "client_cert_configured": bool(profile.auth.values.get("client_cert")),
                "client_key_configured": bool(profile.auth.values.get("client_key")),
            }
        )

    return evidence


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
    access_config=None,
    churn_samples=1,
    churn_interval_seconds=0,
):
    started = time.monotonic()
    LOGGER.info(
        "kafka.start bootstrap_server=%s security_protocol=%s access_config=%s topic=%s consumer_group=%s max_topics=%s max_groups=%s",
        bootstrap_server,
        security_protocol,
        bool(access_config),
        topic,
        consumer_group,
        max_topics,
        max_groups,
    )
    findings = []
    access_resolver = None
    cluster_profile = None

    if access_config:
        LOGGER.info("kafka.access_config.load path=%s", access_config)
        access_resolver = load_kafka_access_config(access_config)

        if not access_resolver.valid:
            LOGGER.warning(
                "kafka.access_config.invalid errors=%s", access_resolver.errors
            )
            findings.append(
                access_profile_finding(
                    "kafka.runtime.access.invalid",
                    "ERROR",
                    "Kafka access config is invalid",
                    "Beacon cannot safely start Kafka diagnostics with invalid access profile configuration.",
                    "Fix the reported access profile validation errors and retry.",
                    {"access_config": access_config, "errors": access_resolver.errors},
                )
            )
            return findings

        findings.extend(access_posture_findings(access_resolver.posture_issues()))
        LOGGER.info(
            "kafka.access_config.loaded profiles=%s posture_findings=%s",
            len(access_resolver.profiles),
            len(findings),
        )

        cluster_profile = access_resolver.profile_for("list_topics")

        if not cluster_profile:
            LOGGER.warning("kafka.access_config.cluster_profile_missing")
            findings.append(
                access_profile_finding(
                    "kafka.runtime.access.cluster_profile.missing",
                    "ERROR",
                    "Kafka access config has no cluster discovery profile",
                    "Beacon needs a profile capable of read-only cluster discovery before it can enumerate Kafka topics.",
                    "Add a cluster or all-scope profile with list_topics capability.",
                    {"access_config": access_config},
                )
            )
            return findings

        findings.append(
            access_profile_finding(
                "kafka.runtime.access.cluster_profile.loaded",
                "INFO",
                f"Kafka access profile '{cluster_profile.name}' selected for cluster discovery",
                "Beacon will use this profile for read-only cluster metadata discovery.",
                "No Kafka mutation operation will be performed.",
                {"profile": cluster_profile.evidence()},
            )
        )

        bootstrap_server = normalize_bootstrap_servers(
            cluster_profile.bootstrap_servers
        )

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
        LOGGER.warning("kafka.server_config.invalid errors=%s", validation_errors)
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
        LOGGER.info("kafka.admin_config.build profile=%s", bool(cluster_profile))
        if cluster_profile:
            config = admin_config_from_profile(cluster_profile)
        else:
            config = build_admin_config(
                bootstrap_server=bootstrap_server,
                security_protocol=security_protocol,
                ca_cert=ca_cert,
                client_cert=client_cert,
                client_key=client_key,
            )

        LOGGER.info("kafka.admin_client.create")
        admin_client = AdminClient(config)
        LOGGER.info("kafka.metadata.list_topics.start timeout=3")
        metadata_started = time.monotonic()
        metadata = admin_client.list_topics(timeout=3)
        LOGGER.info(
            "kafka.metadata.list_topics.complete elapsed=%.2fs",
            time.monotonic() - metadata_started,
        )

        broker_count = len(metadata.brokers)

        all_user_topics = [
            topic_name
            for topic_name in metadata.topics.keys()
            if not topic_name.startswith("__")
        ]
        user_topics = list(all_user_topics)
        topic_scope = "cluster"

        if topic:
            user_topics = [
                topic_name for topic_name in user_topics if topic_name == topic
            ]
            topic_scope = "topic"
        elif consumer_group:
            group_topics = discover_topics_for_consumer_group(
                admin_client=admin_client,
                consumer_group=consumer_group,
            )
            if group_topics:
                user_topics = [
                    topic_name
                    for topic_name in user_topics
                    if topic_name in group_topics
                ]
                topic_scope = "consumer_group_committed_topics"
            else:
                user_topics = []
                topic_scope = "consumer_group_only_no_committed_topics"

        topic_count = len(user_topics)
        LOGGER.info(
            "kafka.metadata.loaded brokers=%s cluster_topics=%s analyzed_topics=%s topic_scope=%s selected_filter_topic=%s consumer_group=%s",
            broker_count,
            len(all_user_topics),
            topic_count,
            topic_scope,
            topic,
            consumer_group,
        )

        findings.append(
            finding(
                "LOW",
                "Kafka cluster connection successful",
                f"Beacon connected successfully. Brokers detected: {broker_count}, user topics detected: {topic_count}.",
                "Beacon used read-only metadata access. No Kafka mutation operation was performed.",
                rule_id="kafka.runtime.connection.success",
                evidence={
                    **connection_evidence(server_config, cluster_profile),
                    "broker_count": broker_count,
                    "cluster_topic_count": len(all_user_topics),
                    "analyzed_topic_count": topic_count,
                    "topic_scope": topic_scope,
                    "topic_filter": topic,
                    "consumer_group_filter": consumer_group,
                },
                confidence="HIGH",
            )
        )

        if topic_scope == "consumer_group_only_no_committed_topics":
            findings.append(
                finding(
                    "INFO",
                    f"Kafka topic diagnostics narrowed to consumer group '{consumer_group}' but no committed topic offsets were found",
                    "Beacon did not run broad topic readiness checks because a consumer group filter was provided and the group had no committed topic offsets.",
                    "Provide a topic filter for topic readiness, or verify whether the consumer group is active and committing offsets.",
                    rule_id="kafka.runtime.topic_scope.no_committed_offsets",
                    evidence={
                        "consumer_group": consumer_group,
                        "topic_scope": topic_scope,
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

        if topic_scope == "cluster" and topic_count > 200:
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

        before = len(findings)
        findings.extend(
            build_partition_health_findings(
                metadata=metadata,
                topic_names=user_topics,
                broker_count=broker_count,
            )
        )
        LOGGER.info(
            "kafka.partition_health.complete added=%s",
            len(findings) - before,
        )

        selected_topics = user_topics[:max_topics]
        LOGGER.info("kafka.topic_models.start selected_topics=%s", len(selected_topics))

        live_topic_models = build_live_topic_models_with_access(
            admin_client=admin_client,
            metadata=metadata,
            topic_names=selected_topics,
            access_resolver=access_resolver,
            findings=findings,
        )
        LOGGER.info("kafka.topic_models.complete models=%s", len(live_topic_models))

        if live_topic_models:
            kafka_config_payload = {"topics": live_topic_models}
            resources = normalize_kafka_config(kafka_config_payload, "runtime-kafka")

            before = len(findings)
            LOGGER.info("kafka.topic_rules.evaluate resources=%s", len(resources))
            findings.extend(
                evaluate(
                    resources,
                    context={"file": "runtime-kafka"},
                )
            )
            LOGGER.info("kafka.topic_rules.complete added=%s", len(findings) - before)

        LOGGER.info("kafka.broker_models.start")
        live_broker_models = build_live_broker_models(
            admin_client=admin_client,
            metadata=metadata,
        )
        LOGGER.info("kafka.broker_models.complete models=%s", len(live_broker_models))

        before = len(findings)
        findings.extend(build_live_quota_findings(live_broker_models))
        LOGGER.info("kafka.quotas.complete added=%s", len(findings) - before)

        before = len(findings)
        LOGGER.info("kafka.acls.start")
        findings.extend(analyze_acl_posture(admin_client))
        LOGGER.info("kafka.acls.complete added=%s", len(findings) - before)

        if live_broker_models:
            kafka_config_payload = {"brokers": live_broker_models}
            resources = normalize_kafka_config(kafka_config_payload, "runtime-kafka")

            before = len(findings)
            LOGGER.info("kafka.broker_rules.evaluate resources=%s", len(resources))
            findings.extend(
                evaluate(
                    resources,
                    context={"file": "runtime-kafka"},
                )
            )
            LOGGER.info("kafka.broker_rules.complete added=%s", len(findings) - before)

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
        LOGGER.info("kafka.connection.failed error=%s", e, exc_info=True)
        findings.append(
            finding(
                "ERROR",
                "Kafka cluster connection failed",
                str(e),
                "Check bootstrap server, network access, security protocol, certificates, and firewall rules.",
                rule_id="kafka.runtime.connection.failed",
                evidence={
                    **connection_evidence(server_config, cluster_profile),
                    "error": str(e),
                },
                confidence="HIGH",
            )
        )
        # If we failed to build or connect the AdminClient, return early.
        LOGGER.info(
            "kafka.complete findings=%s elapsed=%.2fs",
            len(findings),
            time.monotonic() - started,
        )
        return findings
    # Only analyze consumer groups when admin client was created successfully
    if "admin_client" in locals() and admin_client is not None:
        LOGGER.info("kafka.consumer_groups.start")
        consumer_group_admin_client = admin_client
        if access_resolver and consumer_group:
            group_profile = access_resolver.profile_for(
                "describe_consumer_group", consumer_group=consumer_group
            )
            if group_profile:
                findings.append(
                    access_profile_finding(
                        "kafka.runtime.access.consumer_group_profile.loaded",
                        "INFO",
                        f"Kafka access profile '{group_profile.name}' selected for consumer group diagnostics",
                        "Beacon will use this profile for read-only consumer group diagnostics.",
                        "No Kafka offset or group mutation operation will be performed.",
                        {
                            "profile": group_profile.evidence(),
                            "consumer_group": consumer_group,
                        },
                    )
                )
                consumer_group_admin_client = AdminClient(
                    admin_config_from_profile(group_profile)
                )
            else:
                findings.append(
                    access_profile_finding(
                        "kafka.runtime.access.consumer_group_profile.missing",
                        "LOW",
                        "No matching Kafka consumer group access profile found",
                        "Beacon will use the cluster profile for consumer group diagnostics.",
                        "Add a consumer_group or all-scope profile if this group requires separate credentials.",
                        {"consumer_group": consumer_group},
                    )
                )
        before = len(findings)
        findings.extend(
            analyze_consumer_group_lag(
                admin_client=consumer_group_admin_client,
                consumer_group=consumer_group,
                max_groups=max_groups,
                churn_samples=churn_samples,
                churn_interval_seconds=churn_interval_seconds,
            )
        )
        LOGGER.info("kafka.consumer_groups.complete added=%s", len(findings) - before)

    LOGGER.info(
        "kafka.complete findings=%s elapsed=%.2fs",
        len(findings),
        time.monotonic() - started,
    )
    return findings


def build_live_topic_models_with_access(
    admin_client, metadata, topic_names, access_resolver=None, findings=None
):
    if not access_resolver:
        return build_live_topic_models(admin_client, metadata, topic_names)

    topic_models = []

    for topic_name in topic_names:
        profile = access_resolver.profile_for("describe_topic", topic=topic_name)

        if not profile:
            if findings is not None:
                findings.append(
                    access_profile_finding(
                        "kafka.runtime.access.topic_profile.missing",
                        "LOW",
                        f"No matching Kafka topic access profile found for '{topic_name}'",
                        "Beacon discovered this topic but no scoped profile matched it for topic config diagnostics.",
                        "Add a topic or all-scope profile if this topic requires separate credentials.",
                        {"topic": topic_name},
                    )
                )
            profile = access_resolver.profile_for("describe_topic")

        topic_admin_client = admin_client
        if profile:
            if findings is not None:
                findings.append(
                    access_profile_finding(
                        "kafka.runtime.access.topic_profile.loaded",
                        "INFO",
                        f"Kafka access profile '{profile.name}' selected for topic '{topic_name}'",
                        "Beacon will use this profile for read-only topic diagnostics.",
                        "No topic mutation operation will be performed.",
                        {"profile": profile.evidence(), "topic": topic_name},
                    )
                )
            topic_admin_client = AdminClient(admin_config_from_profile(profile))

        topic_models.extend(
            build_live_topic_models(
                admin_client=topic_admin_client,
                metadata=metadata,
                topic_names=[topic_name],
            )
        )

    return topic_models


def access_posture_findings(issues):
    return [
        access_profile_finding(
            issue["rule_id"],
            issue["severity"],
            issue["title"],
            issue["impact"],
            issue["recommendation"],
            issue["evidence"],
        )
        for issue in issues
    ]


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
    churn_samples=1,
    churn_interval_seconds=0,
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
    findings.extend(
        analyze_consumer_group_churn(
            admin_client=admin_client,
            group_ids=group_ids,
            samples=churn_samples,
            interval_seconds=churn_interval_seconds,
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


def build_live_quota_findings(broker_models):
    if not broker_models:
        return []

    producer_quotas = [
        broker.get("producer_quota_bytes_per_second")
        for broker in broker_models
        if broker.get("producer_quota_bytes_per_second") is not None
    ]
    consumer_quotas = [
        broker.get("consumer_quota_bytes_per_second")
        for broker in broker_models
        if broker.get("consumer_quota_bytes_per_second") is not None
    ]

    if producer_quotas and consumer_quotas:
        return [
            finding(
                "LOW",
                "Kafka broker client quotas are configured",
                "Beacon detected producer and consumer byte-rate quota settings in broker configuration.",
                "Validate quota values against tenant isolation and peak traffic requirements.",
                rule_id="kafka.runtime.client_quotas.configured",
                category="operational_safety",
                evidence={
                    "broker_count": len(broker_models),
                    "producer_quota_count": len(producer_quotas),
                    "consumer_quota_count": len(consumer_quotas),
                },
                confidence="HIGH",
            )
        ]

    return [
        finding(
            "MEDIUM",
            "Kafka broker client quotas are not fully configured",
            "Without producer and consumer quotas, a single client or tenant can consume disproportionate broker capacity during spikes.",
            "Configure producer and consumer byte-rate quotas or document equivalent platform-level traffic controls.",
            rule_id="kafka.runtime.client_quotas.missing",
            category="operational_safety",
            evidence={
                "broker_count": len(broker_models),
                "producer_quota_count": len(producer_quotas),
                "consumer_quota_count": len(consumer_quotas),
            },
            confidence="HIGH",
        )
    ]


def analyze_acl_posture(admin_client):
    if not hasattr(admin_client, "describe_acls"):
        return [
            finding(
                "LOW",
                "Kafka ACL posture could not be inspected",
                "The active Kafka client does not expose a read-only ACL describe API.",
                "Provide ACL exports or use a Kafka client/platform that supports describe_acls for authorization posture checks.",
                rule_id="kafka.runtime.acl.analysis_unavailable",
                category="operational_safety",
                evidence={"api": "describe_acls", "available": False},
                confidence="MEDIUM",
            )
        ]

    try:
        acl_filter = build_acl_filter()
        if acl_filter is not None:
            future = admin_client.describe_acls(acl_filter, request_timeout=3)
        else:
            future = admin_client.describe_acls(request_timeout=3)
        result = future.result(timeout=3)
        acl_bindings = list(getattr(result, "acl_bindings", result) or [])
    except Exception as error:
        return [
            finding(
                "LOW",
                "Kafka ACL posture collection failed",
                "Beacon could not inspect ACLs through the read-only Admin API.",
                "Check Describe ACL permissions or provide an ACL export for offline analysis.",
                rule_id="kafka.runtime.acl.collection_failed",
                category="operational_safety",
                evidence={"error": str(error)},
                confidence="MEDIUM",
            )
        ]

    if not acl_bindings:
        return [
            finding(
                "HIGH",
                "Kafka ACL list is empty",
                "An empty ACL list can mean authorization is not enforced or access control is managed outside Kafka.",
                "Verify authorizer configuration and document equivalent platform authorization controls.",
                rule_id="kafka.runtime.acl.none_found",
                category="operational_safety",
                evidence={"acl_count": 0},
                confidence="MEDIUM",
            )
        ]

    broad_acls = [acl_evidence(acl) for acl in acl_bindings if is_broad_allow_acl(acl)]
    if broad_acls:
        return [
            finding(
                "HIGH",
                "Kafka ACLs include broad allow permissions",
                "Broad ACLs can give users or services access beyond the intended topic or consumer-group blast radius.",
                "Replace wildcard or all-operation ACLs with scoped topic, group, and transactional-id permissions.",
                rule_id="kafka.runtime.acl.broad_allow",
                category="operational_safety",
                evidence={
                    "acl_count": len(acl_bindings),
                    "broad_acl_count": len(broad_acls),
                    "broad_acls": broad_acls[:10],
                },
                confidence="HIGH",
            )
        ]

    return [
        finding(
            "LOW",
            "Kafka ACL posture inspected",
            "Beacon inspected Kafka ACL metadata and did not detect broad allow patterns in the sampled ACLs.",
            "Continue enforcing least privilege and review ACL changes during production readiness checks.",
            rule_id="kafka.runtime.acl.posture_inspected",
            category="operational_safety",
            evidence={"acl_count": len(acl_bindings)},
            confidence="HIGH",
        )
    ]


def build_acl_filter():
    try:
        from confluent_kafka.admin import (  # noqa: PLC0415
            AclBindingFilter,
            ResourcePatternType,
            AclOperation,
            AclPermissionType,
        )

        return AclBindingFilter(
            restype=ResourceType.ANY,
            name=None,
            resource_pattern_type=ResourcePatternType.ANY,
            principal=None,
            host=None,
            operation=AclOperation.ANY,
            permission_type=AclPermissionType.ANY,
        )
    except Exception:
        return None


def is_broad_allow_acl(acl):
    evidence = acl_evidence(acl)
    principal = str(evidence.get("principal") or "")
    resource_name = str(evidence.get("resource_name") or "")
    operation = str(evidence.get("operation") or "").upper()
    permission = str(evidence.get("permission_type") or "").upper()
    pattern_type = str(evidence.get("resource_pattern_type") or "").upper()

    if "DENY" in permission:
        return False

    return any(
        [
            principal in {"User:*", "*"},
            resource_name in {"*", ""},
            "ALL" in operation or "ANY" in operation,
            "ANY" in pattern_type,
        ]
    )


def acl_evidence(acl):
    if isinstance(acl, dict):
        return {
            "principal": str(acl.get("principal", "")),
            "host": str(acl.get("host", "")),
            "operation": str(acl.get("operation", "")),
            "permission_type": str(
                acl.get("permission_type", acl.get("permission", ""))
            ),
            "resource_type": str(acl.get("resource_type", acl.get("restype", ""))),
            "resource_name": str(acl.get("resource_name", acl.get("name", ""))),
            "resource_pattern_type": str(
                acl.get("resource_pattern_type", acl.get("pattern_type", ""))
            ),
        }

    return {
        "principal": str(getattr(acl, "principal", "")),
        "host": str(getattr(acl, "host", "")),
        "operation": str(getattr(acl, "operation", "")),
        "permission_type": str(getattr(acl, "permission_type", "")),
        "resource_type": str(
            getattr(acl, "restype", getattr(acl, "resource_type", ""))
        ),
        "resource_name": str(getattr(acl, "name", getattr(acl, "resource_name", ""))),
        "resource_pattern_type": str(
            getattr(
                acl,
                "resource_pattern_type",
                getattr(acl, "pattern_type", ""),
            )
        ),
    }


def analyze_consumer_group_churn(
    admin_client,
    group_ids,
    samples=1,
    interval_seconds=0,
):
    sample_count = max(1, int(samples or 1))
    if sample_count < 2 or not group_ids:
        return []

    snapshots = []

    for sample_index in range(sample_count):
        snapshots.append(consumer_group_member_snapshot(admin_client, group_ids))
        if sample_index < sample_count - 1 and interval_seconds:
            time.sleep(max(0, float(interval_seconds)))

    findings = []

    for group_id in group_ids:
        member_sets = [snapshot.get(group_id, set()) for snapshot in snapshots]
        unique_member_sets = {tuple(sorted(members)) for members in member_sets}
        member_counts = [len(members) for members in member_sets]

        if len(unique_member_sets) >= 3 or member_counts.count(0) >= 2:
            findings.append(
                finding(
                    "HIGH",
                    f"Kafka consumer group '{group_id}' has member churn across samples",
                    "Consumer membership changed repeatedly during the sampling window, which can cause rebalances and lag spikes.",
                    "Inspect rolling deployments, session timeout, heartbeat interval, max.poll.interval.ms, and consumer crashes.",
                    rule_id="kafka.consumer_group.member_churn.high",
                    evidence={
                        "consumer_group": group_id,
                        "samples": sample_count,
                        "member_counts": member_counts,
                        "unique_member_set_count": len(unique_member_sets),
                    },
                    confidence="HIGH",
                )
            )

    return findings


def consumer_group_member_snapshot(admin_client, group_ids):
    descriptions = describe_consumer_groups(admin_client, group_ids)
    snapshot = {}

    for group_id, description in descriptions.items():
        members = getattr(description, "members", []) or []
        snapshot[group_id] = {
            str(
                getattr(member, "member_id", None)
                or getattr(member, "consumer_id", None)
                or getattr(member, "client_id", None)
                or member
            )
            for member in members
        }

    return snapshot


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


def discover_topics_for_consumer_group(admin_client, consumer_group):
    if not consumer_group:
        return set()

    try:
        committed_partitions = fetch_committed_offsets(
            admin_client=admin_client,
            group_id=consumer_group,
        )
    except Exception:
        LOGGER.info(
            "kafka.consumer_group.topic_scope.failed consumer_group=%s",
            consumer_group,
            exc_info=True,
        )
        return set()

    topics = {
        partition.topic
        for partition in committed_partitions
        if partition.topic and not partition.topic.startswith("__")
    }
    LOGGER.info(
        "kafka.consumer_group.topic_scope.complete consumer_group=%s topics=%s",
        consumer_group,
        len(topics),
    )
    return topics


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
    descriptions = describe_consumer_groups(admin_client, group_ids)
    findings = []

    for group_id, description in descriptions.items():
        findings.extend(build_consumer_group_stability_findings(group_id, description))

    return findings


def describe_consumer_groups(admin_client, group_ids):
    if not group_ids or not hasattr(admin_client, "describe_consumer_groups"):
        return {}

    try:
        futures = admin_client.describe_consumer_groups(group_ids, request_timeout=3)
    except TypeError:
        try:
            futures = admin_client.describe_consumer_groups(group_ids)
        except Exception:
            return {}
    except Exception:
        return {}

    descriptions = {}

    for group_id, future in (futures or {}).items():
        try:
            descriptions[group_id] = future.result(timeout=3)
        except Exception:
            continue

    return descriptions


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
