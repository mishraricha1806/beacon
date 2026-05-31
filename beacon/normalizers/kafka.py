from beacon.engine.models import Resource


def normalize_kafka_config(data, source):
    resources = []
    kafka_data = data.get("kafka", data)

    for topic in kafka_data.get("topics", []):
        resources.append(
            Resource(
                type="kafka_topic",
                name=topic.get("name", "unknown-topic"),
                domain="kafka",
                source=source,
                attributes={
                    "replication_factor": topic.get("replication_factor"),
                    "partitions": topic.get("partitions"),
                    "retention_ms": topic.get("retention_ms"),
                    "retention_bytes": topic.get("retention_bytes"),
                    "cleanup_policy": topic.get("cleanup_policy"),
                    "min_insync_replicas": topic.get("min_insync_replicas"),
                    "segment_bytes": topic.get("segment_bytes"),
                    "max_message_bytes": topic.get("max_message_bytes"),
                    "schema_compatibility": topic.get("schema_compatibility"),
                    "owner": topic.get("owner"),
                },
            )
        )

    for broker in kafka_data.get("brokers", []):
        resources.append(
            Resource(
                type="kafka_broker_config",
                name=str(broker.get("id", broker.get("name", "unknown-broker"))),
                domain="kafka",
                source=source,
                attributes={
                    "default_replication_factor": broker.get(
                        "default_replication_factor"
                    ),
                    "offsets_topic_replication_factor": broker.get(
                        "offsets_topic_replication_factor"
                    ),
                    "transaction_state_log_replication_factor": broker.get(
                        "transaction_state_log_replication_factor"
                    ),
                    "log_retention_bytes": broker.get("log_retention_bytes"),
                    "auto_create_topics_enable": broker.get(
                        "auto_create_topics_enable"
                    ),
                    "broker_rack": broker.get("broker_rack"),
                    "security_protocol": broker.get("security_protocol"),
                    "listener_security_protocol_map": broker.get(
                        "listener_security_protocol_map"
                    ),
                    "authorizer_class_name": broker.get("authorizer_class_name"),
                    "allow_everyone_if_no_acl_found": broker.get(
                        "allow_everyone_if_no_acl_found"
                    ),
                    "unclean_leader_election_enable": broker.get(
                        "unclean_leader_election_enable"
                    ),
                    "controlled_shutdown_enable": broker.get(
                        "controlled_shutdown_enable"
                    ),
                    "producer_quota_bytes_per_second": broker.get(
                        "producer_quota_bytes_per_second"
                    ),
                    "consumer_quota_bytes_per_second": broker.get(
                        "consumer_quota_bytes_per_second"
                    ),
                },
            )
        )

    return resources
