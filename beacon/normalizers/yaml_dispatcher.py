from beacon.normalizers.cicd import normalize_cicd_workflow
from beacon.normalizers.cloud import normalize_cloud_inventory
from beacon.normalizers.kafka import normalize_kafka_config
from beacon.normalizers.kubernetes import normalize_kubernetes_config
from beacon.normalizers.runtime import normalize_runtime_sections
from beacon.normalizers.topology import normalize_topology


def normalize_yaml_document(data, source):
    if not isinstance(data, dict):
        return []

    if "topics" in data or "kafka" in data:
        return normalize_kafka_config(data, source)

    if "kind" in data and "apiVersion" in data:
        return normalize_kubernetes_config(data, source)

    if "jobs" in data:
        return normalize_cicd_workflow(data, source)

    runtime_resources = normalize_runtime_sections(data, source)

    if runtime_resources:
        return runtime_resources

    if "cloud_inventory" in data:
        return normalize_cloud_inventory(data.get("cloud_inventory", {}), source)

    if "topology" in data:
        return normalize_topology(data.get("topology", {}), source)

    return []
