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
                },
            )
        )

    return resources
