from beacon.engine.models import Resource


def normalize_kafka_config(data, source):
    resources = []

    for topic in data.get("topics", []):
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

    return resources


def normalize_terraform_config(data, source):
    resources = []
    terraform_resources = data.get("resource", [])

    for block in terraform_resources:
        for resource_type, instances in block.items():
            for name, config in instances.items():
                if is_object_storage_resource(resource_type):
                    resources.append(
                        Resource(
                            type="object_storage_bucket",
                            name=name,
                            domain="object_storage",
                            source=source,
                            attributes={
                                "provider_resource_type": resource_type,
                                "config": config,
                            },
                        )
                    )

                if is_iam_resource(resource_type):
                    resources.append(
                        Resource(
                            type="iam_policy",
                            name=name,
                            domain="cloud_identity",
                            source=source,
                            attributes={
                                "provider_resource_type": resource_type,
                                "config": config,
                                "raw_config": str(config),
                            },
                        )
                    )

    return resources


def is_object_storage_resource(resource_type):
    return resource_type in {
        "aws_s3_bucket",
        "aws_s3_bucket_public_access_block",
        "google_storage_bucket",
        "azurerm_storage_account",
    }


def is_iam_resource(resource_type):
    return resource_type in {
        "aws_iam_policy",
        "google_project_iam_binding",
        "azurerm_role_assignment",
    }


def normalize_kubernetes_config(data, source):
    if not isinstance(data, dict):
        return []

    kind = data.get("kind")
    metadata = data.get("metadata", {})
    name = metadata.get("name", "unknown-workload")

    if kind not in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}:
        return []

    spec = data.get("spec", {})
    template = spec.get("template", {})
    pod_spec = template.get("spec", {})
    containers = pod_spec.get("containers", [])
    replicas = spec.get("replicas")

    resources = []

    for container in containers:
        security_context = container.get("securityContext", {})

        resources.append(
            Resource(
                type="k8s_workload_container",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "replicas": replicas,
                    "container": container.get("name", "unknown-container"),
                    "image": container.get("image", ""),
                    "resources": container.get("resources", {}),
                    "has_readiness_probe": "readinessProbe" in container,
                    "has_liveness_probe": "livenessProbe" in container,
                    "privileged": security_context.get("privileged"),
                },
            )
        )

    return resources


def normalize_yaml_document(data, source):
    if not isinstance(data, dict):
        return []

    if "topics" in data:
        return normalize_kafka_config(data, source)

    if "kind" in data and "apiVersion" in data:
        return normalize_kubernetes_config(data, source)

    return []
