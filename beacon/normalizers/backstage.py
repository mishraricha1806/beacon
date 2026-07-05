from beacon.engine.models import Resource


def normalize_backstage_catalog(data, source):
    if not is_backstage_entity(data):
        return []

    kind = str(data.get("kind") or "").lower()
    if kind != "component":
        return []

    metadata = data.get("metadata") or {}
    spec = data.get("spec") or {}
    annotations = metadata.get("annotations") or {}
    labels = metadata.get("labels") or {}
    name = metadata.get("name") or "unknown-service"

    return [
        Resource(
            type="topology_service",
            name=name,
            domain="topology",
            source=source,
            attributes={
                "owner": backstage_owner(spec),
                "criticality": backstage_criticality(metadata, spec),
                "business_impact": backstage_business_impact(metadata, spec),
                "aliases": backstage_aliases(metadata),
                "instances": None,
                "depends_on": backstage_relations(spec, "dependsOn"),
                "dependents": backstage_relations(spec, "dependencyOf"),
                "system": spec.get("system"),
                "lifecycle": spec.get("lifecycle"),
                "component_type": spec.get("type"),
                "backstage_entity_ref": backstage_entity_ref(kind, name, metadata),
                "annotations": annotations,
                "labels": labels,
            },
        )
    ]


def is_backstage_entity(data):
    if not isinstance(data, dict):
        return False
    api_version = str(data.get("apiVersion") or "").lower()
    return api_version.startswith("backstage.io/")


def backstage_owner(spec):
    owner = spec.get("owner")
    if isinstance(owner, str):
        return owner.removeprefix("group:").removeprefix("user:")
    return owner


def backstage_criticality(metadata, spec):
    annotations = metadata.get("annotations") or {}
    labels = metadata.get("labels") or {}
    return (
        spec.get("criticality")
        or annotations.get("beacon.io/criticality")
        or annotations.get("pagerduty.com/service-tier")
        or labels.get("criticality")
        or labels.get("tier")
    )


def backstage_business_impact(metadata, spec):
    annotations = metadata.get("annotations") or {}
    return (
        spec.get("businessImpact")
        or spec.get("business_impact")
        or annotations.get("beacon.io/business-impact")
    )


def backstage_aliases(metadata):
    annotations = metadata.get("annotations") or {}
    aliases = annotations.get("beacon.io/aliases") or ""
    if isinstance(aliases, str):
        return [alias.strip() for alias in aliases.split(",") if alias.strip()]
    if isinstance(aliases, list):
        return aliases
    return []


def backstage_relations(spec, key):
    values = spec.get(key) or []
    if isinstance(values, str):
        values = [values]
    return [normalize_entity_ref(value) for value in values]


def normalize_entity_ref(value):
    value = str(value)
    if ":" in value:
        value = value.split(":", 1)[1]
    if "/" in value:
        value = value.rsplit("/", 1)[1]
    return value


def backstage_entity_ref(kind, name, metadata):
    namespace = metadata.get("namespace") or "default"
    return f"{kind}:{namespace}/{name}"
