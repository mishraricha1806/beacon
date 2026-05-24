def normalize_kafka_topics(data):
    resources = []

    topics = data.get("topics", [])

    for topic in topics:
        resources.append(
            {
                "type": "kafka_topic",
                "name": topic.get("name"),
                "replication_factor": topic.get(
                    "replication_factor"
                ),
                "partitions": topic.get("partitions"),
                "retention_ms": topic.get("retention_ms"),
                "retention_bytes": topic.get(
                    "retention_bytes"
                ),
                "cleanup_policy": topic.get(
                    "cleanup_policy"
                ),
                "min_insync_replicas": topic.get(
                    "min_insync_replicas"
                ),
                "max_message_bytes": topic.get(
                    "max_message_bytes"
                ),
            }
        )

    return resources