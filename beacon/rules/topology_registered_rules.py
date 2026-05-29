from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_topology_finding(resource, rule_id, category, severity, title, impact, recommendation, evidence, tags=None):
    return Finding(
        rule_id=rule_id,
        domain="topology",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def high_blast_radius(resource, context):
    dependents = resource.attributes.get("dependents", [])
    critical = resource.attributes.get("criticality") in {"critical", "high"}

    if len(dependents) < 3 and not (critical and len(dependents) >= 2):
        return None

    return build_topology_finding(
        resource,
        "topology.service.blast_radius.high",
        "resiliency",
        "HIGH",
        f"Service '{resource.name}' has high blast radius",
        "A failure in this service can affect multiple downstream services or critical flows.",
        "Review redundancy, graceful degradation, dependency timeouts, and incident runbooks for this service.",
        {
            "service": resource.name,
            "criticality": resource.attributes.get("criticality"),
            "dependents": dependents,
            "dependent_count": len(dependents),
        },
        ["topology", "blast-radius", "resiliency"],
    )


def single_instance_critical_service(resource, context):
    if resource.attributes.get("criticality") not in {"critical", "high"}:
        return None

    instances = resource.attributes.get("instances")

    if instances is None or instances > 1:
        return None

    return build_topology_finding(
        resource,
        "topology.service.critical_single_instance",
        "resiliency",
        "CRITICAL",
        f"Critical service '{resource.name}' has a single instance",
        "A single-instance critical service creates a direct availability bottleneck.",
        "Run multiple instances across failure domains or document an approved singleton exception.",
        {
            "service": resource.name,
            "criticality": resource.attributes.get("criticality"),
            "instances": instances,
        },
        ["topology", "availability", "resiliency"],
    )


def missing_owner(resource, context):
    if resource.attributes.get("owner"):
        return None

    return build_topology_finding(
        resource,
        "topology.service.owner.missing",
        "operational_safety",
        "LOW",
        f"Service '{resource.name}' has no owner",
        "Missing ownership slows incident routing and operational accountability.",
        "Assign an owner/team for each production service.",
        {"service": resource.name, "owner": None},
        ["topology", "ownership"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="topology",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["topology_service"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "topology.service.blast_radius.high",
    "resiliency",
    "HIGH",
    "Service blast radius high",
    "Detects services with many dependents or critical downstream impact.",
    high_blast_radius,
    ["topology", "blast-radius"],
)

register(
    "topology.service.critical_single_instance",
    "resiliency",
    "CRITICAL",
    "Critical service single instance",
    "Detects critical services running as a single instance.",
    single_instance_critical_service,
    ["topology", "availability"],
)

register(
    "topology.service.owner.missing",
    "operational_safety",
    "LOW",
    "Service owner missing",
    "Detects topology services without owners.",
    missing_owner,
    ["topology", "ownership"],
)
