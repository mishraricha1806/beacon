from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_k8s_finding(
    resource,
    rule_id,
    category,
    severity,
    title,
    impact,
    recommendation,
    evidence,
    tags=None,
):
    return Finding(
        rule_id=rule_id,
        domain="kubernetes",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def workload_replicas_single(resource, context):
    replicas = resource.attributes.get("replicas")

    if replicas != 1:
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.replicas.single",
        "resiliency",
        "HIGH",
        f"Kubernetes workload '{resource.name}' has only one replica",
        "Single replica workloads may become unavailable during pod or node failure.",
        "Use at least 2 replicas for production services unless intentionally singleton.",
        {"workload": resource.name, "replicas": replicas},
        ["kubernetes", "availability", "resiliency"],
    )


def workload_resources_missing(resource, context):
    resources = resource.attributes.get("resources", {})
    container = resource.attributes.get("container")

    if "requests" in resources and "limits" in resources:
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.resources.missing",
        "scalability",
        "HIGH",
        f"Container '{container}' in workload '{resource.name}' is missing resources",
        "Missing CPU/memory boundaries can cause unstable scheduling and noisy-neighbor issues.",
        "Define CPU/memory requests and limits for production workloads.",
        {"workload": resource.name, "container": container, "resources": resources},
        ["kubernetes", "resources", "scheduling"],
    )


def workload_probes_missing(resource, context):
    has_readiness = resource.attributes.get("has_readiness_probe")
    has_liveness = resource.attributes.get("has_liveness_probe")
    container = resource.attributes.get("container")

    if has_readiness and has_liveness:
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.probes.missing",
        "operational_safety",
        "HIGH",
        f"Container '{container}' in workload '{resource.name}' is missing probes",
        "Missing probes can cause bad traffic routing and delayed failure recovery.",
        "Define readiness and liveness probes for production workloads.",
        {
            "workload": resource.name,
            "container": container,
            "has_readiness_probe": has_readiness,
            "has_liveness_probe": has_liveness,
        },
        ["kubernetes", "health-checks", "recovery"],
    )


def container_privileged(resource, context):
    privileged = resource.attributes.get("privileged")
    container = resource.attributes.get("container")

    if privileged is not True:
        return None

    return build_k8s_finding(
        resource,
        "k8s.container.privileged",
        "operational_safety",
        "CRITICAL",
        f"Container '{container}' in workload '{resource.name}' is privileged",
        "Privileged containers increase cluster blast radius.",
        "Avoid privileged containers unless explicitly required and approved.",
        {"workload": resource.name, "container": container, "privileged": privileged},
        ["kubernetes", "security", "privileged"],
    )


def image_latest_tag(resource, context):
    image = resource.attributes.get("image", "")
    container = resource.attributes.get("container")

    if image and ":" in image and not image.endswith(":latest"):
        return None

    return build_k8s_finding(
        resource,
        "k8s.image.latest_tag",
        "operational_safety",
        "MEDIUM",
        f"Container '{container}' in workload '{resource.name}' uses an unsafe image tag",
        "Mutable image tags make deployments less predictable and rollback harder.",
        "Use immutable versioned image tags or image digests.",
        {"workload": resource.name, "container": container, "image": image},
        ["kubernetes", "deployment", "rollback"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="kubernetes",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["k8s_workload_container"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "k8s.workload.replicas.single",
    "resiliency",
    "HIGH",
    "Kubernetes single replica workload",
    "Detects production workloads with one replica.",
    workload_replicas_single,
    ["kubernetes", "availability"],
)
register(
    "k8s.workload.resources.missing",
    "scalability",
    "HIGH",
    "Kubernetes resources missing",
    "Detects containers missing requests or limits.",
    workload_resources_missing,
    ["kubernetes", "resources"],
)
register(
    "k8s.workload.probes.missing",
    "operational_safety",
    "HIGH",
    "Kubernetes probes missing",
    "Detects containers missing readiness or liveness probes.",
    workload_probes_missing,
    ["kubernetes", "probes"],
)
register(
    "k8s.container.privileged",
    "operational_safety",
    "CRITICAL",
    "Kubernetes privileged container",
    "Detects privileged containers.",
    container_privileged,
    ["kubernetes", "security"],
)
register(
    "k8s.image.latest_tag",
    "operational_safety",
    "MEDIUM",
    "Kubernetes latest image tag",
    "Detects mutable or missing image tags.",
    image_latest_tag,
    ["kubernetes", "deployment"],
)
