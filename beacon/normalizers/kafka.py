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
                    "delete_retention_ms": topic.get("delete_retention_ms"),
                    "min_cleanable_dirty_ratio": topic.get("min_cleanable_dirty_ratio"),
                    "key_cardinality_estimate": topic.get("key_cardinality_estimate"),
                    "replica_placements": topic.get("replica_placements", []),
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
                    "default_replication_factor": broker.get("default_replication_factor"),
                    "offsets_topic_replication_factor": broker.get(
                        "offsets_topic_replication_factor"
                    ),
                    "transaction_state_log_replication_factor": broker.get(
                        "transaction_state_log_replication_factor"
                    ),
                    "log_retention_bytes": broker.get("log_retention_bytes"),
                    "auto_create_topics_enable": broker.get("auto_create_topics_enable"),
                    "broker_rack": broker.get("broker_rack"),
                    "security_protocol": broker.get("security_protocol"),
                    "listener_security_protocol_map": broker.get("listener_security_protocol_map"),
                    "authorizer_class_name": broker.get("authorizer_class_name"),
                    "allow_everyone_if_no_acl_found": broker.get("allow_everyone_if_no_acl_found"),
                    "unclean_leader_election_enable": broker.get("unclean_leader_election_enable"),
                    "controlled_shutdown_enable": broker.get("controlled_shutdown_enable"),
                    "producer_quota_bytes_per_second": broker.get(
                        "producer_quota_bytes_per_second"
                    ),
                    "consumer_quota_bytes_per_second": broker.get(
                        "consumer_quota_bytes_per_second"
                    ),
                },
            )
        )

    for producer in kafka_data.get("producers", []):
        resources.append(
            Resource(
                type="kafka_producer_config",
                name=producer.get("name", "unknown-producer"),
                domain="kafka",
                source=source,
                attributes={
                    "topic": producer.get("topic"),
                    "acks": producer.get("acks"),
                    "enable_idempotence": producer.get("enable_idempotence"),
                    "retries": producer.get("retries"),
                    "max_in_flight_requests_per_connection": producer.get(
                        "max_in_flight_requests_per_connection"
                    ),
                    "compression_type": producer.get("compression_type"),
                    "delivery_timeout_ms": producer.get("delivery_timeout_ms"),
                    "request_timeout_ms": producer.get("request_timeout_ms"),
                },
            )
        )

    for consumer in kafka_data.get("consumers", []):
        resources.append(
            Resource(
                type="kafka_consumer_config",
                name=consumer.get("name", "unknown-consumer"),
                domain="kafka",
                source=source,
                attributes={
                    "topic": consumer.get("topic"),
                    "group_id": consumer.get("group_id"),
                    "partitions": consumer.get("partitions"),
                    "consumer_concurrency": consumer.get("consumer_concurrency"),
                    "enable_auto_commit": consumer.get("enable_auto_commit"),
                    "auto_offset_reset": consumer.get("auto_offset_reset"),
                    "max_poll_interval_ms": consumer.get("max_poll_interval_ms"),
                    "session_timeout_ms": consumer.get("session_timeout_ms"),
                    "heartbeat_interval_ms": consumer.get("heartbeat_interval_ms"),
                    "retry_max_attempts": consumer.get("retry_max_attempts"),
                    "dlq_topic": consumer.get("dlq_topic"),
                },
            )
        )

    return resources
