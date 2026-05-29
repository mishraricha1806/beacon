from beacon.engine.models import Resource
from beacon.normalizers.common import (
    is_cloud_resource,
    is_iam_resource,
    is_object_storage_resource,
)


def normalize_cloud_inventory(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for item in data.get("resources", []):
        resource_type = item.get("type")
        name = item.get("name", "unknown-resource")
        config = item.get("config", item)

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

        if is_cloud_resource(resource_type):
            resources.append(
                Resource(
                    type="cloud_resource",
                    name=name,
                    domain="cloud",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": config,
                    },
                )
            )

    return resources
