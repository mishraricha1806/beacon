"""Compatibility facade for domain-specific normalizers."""

from beacon.normalizers.backstage import normalize_backstage_catalog
from beacon.normalizers.cicd import (
    is_deploy_like_job,
    normalize_cicd_workflow,
    normalize_workflow_triggers,
)
from beacon.normalizers.cloud import normalize_cloud_inventory
from beacon.normalizers.common import (
    is_cloud_resource,
    is_iam_resource,
    is_object_storage_resource,
    normalize_hcl_identifier,
)
from beacon.normalizers.kafka import normalize_kafka_config
from beacon.normalizers.kubernetes import (
    normalize_kubernetes_config,
    normalize_kubernetes_runtime,
)
from beacon.normalizers.runtime import (
    normalize_api_runtime,
    normalize_database_runtime,
    normalize_flow_runtime,
    normalize_runtime_sections,
    normalize_storage_runtime,
)
from beacon.normalizers.terraform import (
    iter_terraform_json_resources,
    iter_terraform_module_resources,
    iter_terraform_value_resources,
    normalize_terraform_config,
    normalize_terraform_json,
)
from beacon.normalizers.topology import normalize_topology
from beacon.normalizers.yaml_dispatcher import normalize_yaml_document

__all__ = [
    "is_cloud_resource",
    "is_deploy_like_job",
    "is_iam_resource",
    "is_object_storage_resource",
    "iter_terraform_json_resources",
    "iter_terraform_module_resources",
    "iter_terraform_value_resources",
    "normalize_api_runtime",
    "normalize_backstage_catalog",
    "normalize_cicd_workflow",
    "normalize_cloud_inventory",
    "normalize_database_runtime",
    "normalize_flow_runtime",
    "normalize_hcl_identifier",
    "normalize_kafka_config",
    "normalize_kubernetes_config",
    "normalize_kubernetes_runtime",
    "normalize_runtime_sections",
    "normalize_storage_runtime",
    "normalize_terraform_config",
    "normalize_terraform_json",
    "normalize_topology",
    "normalize_workflow_triggers",
    "normalize_yaml_document",
]
