from beacon.engine.models import Resource
from beacon.normalizers.common import (
    is_cloud_resource,
    is_iam_resource,
    is_object_storage_resource,
    normalize_hcl_identifier,
)


def normalize_terraform_config(data, source):
    resources = []
    terraform_resources = data.get("resource", [])

    for block in terraform_resources:
        for resource_type, instances in block.items():
            resource_type = normalize_hcl_identifier(resource_type)

            for name, config in instances.items():
                name = normalize_hcl_identifier(name)
                resources.extend(
                    build_infra_resources(resource_type, name, config, source)
                )

    return resources


def normalize_terraform_json(data, source):
    resources = []

    for item in iter_terraform_json_resources(data):
        resources.extend(
            build_infra_resources(
                item.get("type"),
                item.get("name", "unknown-resource"),
                item.get("values", {}),
                source,
            )
        )

    return resources


def build_infra_resources(resource_type, name, config, source):
    resources = []

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


def iter_terraform_json_resources(data):
    if not isinstance(data, dict):
        return

    for change in data.get("resource_changes", []):
        after = change.get("change", {}).get("after")

        if after is None:
            continue

        yield {
            "type": change.get("type"),
            "name": change.get("name"),
            "values": after,
        }

    planned_values = data.get("planned_values", {})
    yield from iter_terraform_value_resources(planned_values)

    values = data.get("values", {})
    yield from iter_terraform_value_resources(values)


def iter_terraform_value_resources(values):
    root_module = values.get("root_module") if isinstance(values, dict) else None

    if not isinstance(root_module, dict):
        return

    yield from iter_terraform_module_resources(root_module)


def iter_terraform_module_resources(module):
    for resource in module.get("resources", []):
        yield {
            "type": resource.get("type"),
            "name": resource.get("name"),
            "values": resource.get("values", {}),
        }

    for child in module.get("child_modules", []):
        yield from iter_terraform_module_resources(child)
