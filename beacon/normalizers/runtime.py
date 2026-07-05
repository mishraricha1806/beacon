from beacon.engine.models import Resource
from beacon.normalizers.kubernetes import normalize_kubernetes_runtime


def normalize_runtime_sections(data, source):
    resources = []

    if "kubernetes_runtime" in data:
        resources.extend(normalize_kubernetes_runtime(data.get("kubernetes_runtime", {}), source))

    if "flow_runtime" in data:
        resources.extend(normalize_flow_runtime(data.get("flow_runtime", {}), source))

    if "api_runtime" in data:
        resources.extend(normalize_api_runtime(data.get("api_runtime", {}), source))

    if "database_runtime" in data:
        resources.extend(normalize_database_runtime(data.get("database_runtime", {}), source))

    if "storage_runtime" in data:
        resources.extend(normalize_storage_runtime(data.get("storage_runtime", {}), source))

    return resources


def normalize_api_runtime(data, source):
    if not isinstance(data, dict):
        return []

    services = data.get("services", [])

    if not services and data.get("name"):
        services = [data]

    resources = []

    for service in services:
        resources.append(
            Resource(
                type="api_runtime_service",
                name=service.get("name", "unknown-api"),
                domain="api",
                source=source,
                attributes={
                    "latency_p95_ms": service.get("latency_p95_ms"),
                    "error_rate_percent": service.get("error_rate_percent"),
                    "timeout_rate_percent": service.get("timeout_rate_percent"),
                    "retry_rate_percent": service.get("retry_rate_percent"),
                    "saturation_percent": service.get("saturation_percent"),
                    "recent_deployment": service.get("recent_deployment", False),
                },
            )
        )

    return resources


def normalize_database_runtime(data, source):
    if not isinstance(data, dict):
        return []

    databases = data.get("databases", [])

    if not databases and data.get("name"):
        databases = [data]

    resources = []

    for database in databases:
        resources.append(
            Resource(
                type="database_runtime_instance",
                name=database.get("name", "unknown-database"),
                domain="database",
                source=source,
                attributes={
                    "engine": database.get("engine"),
                    "latency_ms": database.get("latency_ms"),
                    "connection_pool_utilization_percent": database.get(
                        "connection_pool_utilization_percent"
                    ),
                    "lock_waits_high": database.get("lock_waits_high", False),
                    "replication_lag_seconds": database.get("replication_lag_seconds"),
                    "storage_used_percent": database.get("storage_used_percent"),
                },
            )
        )

    return resources


def normalize_storage_runtime(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for item in data.get("resources", []):
        resources.append(
            Resource(
                type="storage_runtime_resource",
                name=item.get("name", "unknown-storage"),
                domain="storage",
                source=source,
                attributes={
                    "resource_type": item.get("type"),
                    "used_percent": item.get("used_percent"),
                    "growth_percent_7d": item.get("growth_percent_7d"),
                    "iops_saturation_percent": item.get("iops_saturation_percent"),
                    "backup_age_hours": item.get("backup_age_hours"),
                },
            )
        )

    return resources


def normalize_flow_runtime(data, source):
    if not isinstance(data, dict):
        return []

    flow_name = data.get("name", "unknown-flow")
    signals = data.get("signals", {})
    owner = data.get("owner") or data.get("team")
    criticality = data.get("criticality") or data.get("tier")
    business_impact = data.get("business_impact")
    blast_radius = data.get("blast_radius", {})
    affected_services = data.get("affected_services") or data.get("services") or []

    resources = [
        Resource(
            type="flow_runtime",
            name=flow_name,
            domain="flow",
            source=source,
            attributes={
                "name": flow_name,
                "signals": signals,
                "components": data.get("components", {}),
                "owner": owner,
                "criticality": criticality,
                "business_impact": business_impact,
                "blast_radius": blast_radius,
                "affected_services": affected_services,
            },
        )
    ]

    for component_name, component in data.get("components", {}).items():
        if not isinstance(component, dict):
            continue

        resources.append(
            Resource(
                type="flow_component_runtime",
                name=component_name,
                domain="flow",
                source=source,
                attributes={
                    "flow": flow_name,
                    "component_type": component.get("type"),
                    "signals": component.get("signals", {}),
                    "depends_on": component.get("depends_on", []) or [],
                    "owner": component.get("owner") or owner,
                    "criticality": component.get("criticality") or criticality,
                    "business_impact": component.get("business_impact") or business_impact,
                    "blast_radius": component.get("blast_radius") or blast_radius,
                    "affected_services": component.get("affected_services") or affected_services,
                },
            )
        )

    return resources
