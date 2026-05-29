from beacon.engine.models import Resource


def normalize_topology(data, source):
    if not isinstance(data, dict):
        return []

    services = data.get("services", [])
    service_names = {service.get("name") for service in services}
    dependents_by_service = {name: [] for name in service_names if name}

    for service in services:
        service_name = service.get("name")

        for dependency in service.get("depends_on", []) or []:
            if dependency in dependents_by_service:
                dependents_by_service[dependency].append(service_name)

    resources = []

    for service in services:
        name = service.get("name", "unknown-service")
        resources.append(
            Resource(
                type="topology_service",
                name=name,
                domain="topology",
                source=source,
                attributes={
                    "owner": service.get("owner"),
                    "criticality": service.get("criticality"),
                    "instances": service.get("instances"),
                    "depends_on": service.get("depends_on", []) or [],
                    "dependents": dependents_by_service.get(name, []),
                },
            )
        )

    return resources
