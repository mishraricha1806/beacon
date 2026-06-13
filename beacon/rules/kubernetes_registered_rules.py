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


def selector_matches_labels(selector, labels):
    selector = selector or {}
    labels = labels or {}
    return all(labels.get(key) == value for key, value in selector.items())


def workload_topology_spread_missing(resource, context):
    replicas = resource.attributes.get("replicas")

    if replicas is None or replicas < 3:
        return None

    if resource.attributes.get("has_topology_spread_constraints") or resource.attributes.get(
        "has_pod_anti_affinity"
    ):
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.topology_spread.missing",
        "resiliency",
        "HIGH",
        f"Kubernetes workload '{resource.name}' lacks topology spread protection",
        "Replicated workloads without topology spread or pod anti-affinity can concentrate replicas in one node or failure domain.",
        "Define topologySpreadConstraints or required podAntiAffinity for replicated production workloads.",
        {
            "workload": resource.name,
            "replicas": replicas,
            "has_topology_spread_constraints": resource.attributes.get(
                "has_topology_spread_constraints"
            ),
            "has_pod_anti_affinity": resource.attributes.get("has_pod_anti_affinity"),
        },
        ["kubernetes", "resiliency", "topology-spread"],
    )


def workload_pdb_missing(resource, context):
    replicas = resource.attributes.get("replicas")
    labels = resource.attributes.get("labels") or {}

    if replicas is None or replicas < 2 or not labels:
        return None

    namespace = resource.attributes.get("namespace")
    budgets = [
        item
        for item in context.get("resources", [])
        if item.type == "k8s_pod_disruption_budget"
        and item.attributes.get("namespace") == namespace
    ]

    if any(
        selector_matches_labels(item.attributes.get("selector_labels"), labels) for item in budgets
    ):
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.pod_disruption_budget.missing",
        "recovery_readiness",
        "HIGH",
        f"Kubernetes workload '{resource.name}' has no PodDisruptionBudget",
        "Without a PodDisruptionBudget, voluntary disruptions can reduce replica count below safe availability targets during maintenance or upgrades.",
        "Define a PodDisruptionBudget for replicated production workloads and align minAvailable/maxUnavailable with rollout expectations.",
        {
            "workload": resource.name,
            "namespace": namespace,
            "replicas": replicas,
            "labels": labels,
        },
        ["kubernetes", "availability", "pdb"],
    )


def workload_network_policy_missing(resource, context):
    labels = resource.attributes.get("labels") or {}

    if not labels:
        return None

    namespace = resource.attributes.get("namespace")
    policies = [
        item
        for item in context.get("resources", [])
        if item.type == "k8s_network_policy" and item.attributes.get("namespace") == namespace
    ]

    if any(
        selector_matches_labels(item.attributes.get("pod_selector"), labels) for item in policies
    ):
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.network_policy.missing",
        "operational_safety",
        "HIGH",
        f"Kubernetes workload '{resource.name}' has no matching NetworkPolicy",
        "Workloads without network policy isolation can accept unintended east-west or ingress traffic inside the cluster.",
        "Define a least-privilege NetworkPolicy that matches the workload labels and explicitly permits approved traffic paths.",
        {
            "workload": resource.name,
            "namespace": namespace,
            "labels": labels,
        },
        ["kubernetes", "security", "network-policy"],
    )


def workload_host_namespace_enabled(resource, context):
    enabled = {
        "host_network": resource.attributes.get("host_network"),
        "host_pid": resource.attributes.get("host_pid"),
        "host_ipc": resource.attributes.get("host_ipc"),
    }
    active = [key for key, value in enabled.items() if value is True]

    if not active:
        return None

    return build_k8s_finding(
        resource,
        "k8s.workload.host_namespace.enabled",
        "operational_safety",
        "HIGH",
        f"Kubernetes workload '{resource.name}' shares host namespaces",
        "Sharing host network, PID, or IPC namespaces expands cluster blast radius and weakens workload isolation.",
        "Avoid hostNetwork, hostPID, and hostIPC for production workloads unless explicitly approved and isolated.",
        {
            "workload": resource.name,
            "enabled_settings": active,
        },
        ["kubernetes", "security", "isolation"],
    )


def container_run_as_non_root_missing(resource, context):
    value = resource.attributes.get("run_as_non_root")
    container = resource.attributes.get("container")

    if value is True:
        return None

    return build_k8s_finding(
        resource,
        "k8s.container.run_as_non_root.missing",
        "operational_safety",
        "HIGH",
        f"Container '{container}' in workload '{resource.name}' does not enforce non-root execution",
        "Containers that can run as root increase compromise impact and weaken pod security boundaries.",
        "Set runAsNonRoot=true and use an image with a non-root user for production workloads.",
        {
            "workload": resource.name,
            "container": container,
            "run_as_non_root": value,
        },
        ["kubernetes", "security", "non-root"],
    )


def container_allow_privilege_escalation_enabled(resource, context):
    value = resource.attributes.get("allow_privilege_escalation")
    container = resource.attributes.get("container")

    if value is False:
        return None

    return build_k8s_finding(
        resource,
        "k8s.container.allow_privilege_escalation.enabled",
        "operational_safety",
        "HIGH",
        f"Container '{container}' in workload '{resource.name}' allows privilege escalation",
        "Privilege escalation increases the chance that a compromised process can gain broader container capabilities.",
        "Set allowPrivilegeEscalation=false unless the workload has an approved exception.",
        {
            "workload": resource.name,
            "container": container,
            "allow_privilege_escalation": value,
        },
        ["kubernetes", "security", "privilege-escalation"],
    )


def container_read_only_root_filesystem_disabled(resource, context):
    value = resource.attributes.get("read_only_root_filesystem")
    container = resource.attributes.get("container")

    if value is True:
        return None

    return build_k8s_finding(
        resource,
        "k8s.container.read_only_root_filesystem.disabled",
        "operational_safety",
        "MEDIUM",
        f"Container '{container}' in workload '{resource.name}' does not use a read-only root filesystem",
        "Writable root filesystems increase tampering risk and make runtime drift harder to detect.",
        "Use readOnlyRootFilesystem=true and mount only the writable paths the workload explicitly needs.",
        {
            "workload": resource.name,
            "container": container,
            "read_only_root_filesystem": value,
        },
        ["kubernetes", "security", "filesystem"],
    )


def container_seccomp_profile_missing(resource, context):
    profile = resource.attributes.get("seccomp_profile") or {}
    profile_type = profile.get("type") if isinstance(profile, dict) else profile
    container = resource.attributes.get("container")

    if profile_type:
        return None

    return build_k8s_finding(
        resource,
        "k8s.container.seccomp_profile.missing",
        "operational_safety",
        "MEDIUM",
        f"Container '{container}' in workload '{resource.name}' has no seccomp profile",
        "Missing seccomp configuration leaves syscall filtering undefined and weakens workload hardening.",
        "Set seccompProfile.type to RuntimeDefault or an approved localhost profile for production workloads.",
        {
            "workload": resource.name,
            "container": container,
            "seccomp_profile": profile,
        },
        ["kubernetes", "security", "seccomp"],
    )


def register(
    rule_id,
    category,
    severity,
    title,
    description,
    evaluator,
    tags,
    supported_resource_types=None,
):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="kubernetes",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=supported_resource_types or ["k8s_workload_container"],
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
register(
    "k8s.workload.topology_spread.missing",
    "resiliency",
    "HIGH",
    "Kubernetes topology spread missing",
    "Detects replicated workloads without topology spread constraints or pod anti-affinity.",
    workload_topology_spread_missing,
    ["kubernetes", "availability", "topology-spread"],
    supported_resource_types=["k8s_workload"],
)
register(
    "k8s.workload.pod_disruption_budget.missing",
    "recovery_readiness",
    "HIGH",
    "Kubernetes PodDisruptionBudget missing",
    "Detects replicated workloads without a matching PodDisruptionBudget in the same manifest set.",
    workload_pdb_missing,
    ["kubernetes", "availability", "pdb"],
    supported_resource_types=["k8s_workload"],
)
register(
    "k8s.workload.network_policy.missing",
    "operational_safety",
    "HIGH",
    "Kubernetes NetworkPolicy missing",
    "Detects workloads without a matching NetworkPolicy in the same manifest set.",
    workload_network_policy_missing,
    ["kubernetes", "security", "network-policy"],
    supported_resource_types=["k8s_workload"],
)
register(
    "k8s.workload.host_namespace.enabled",
    "operational_safety",
    "HIGH",
    "Kubernetes host namespace sharing enabled",
    "Detects workloads that enable host network, PID, or IPC namespaces.",
    workload_host_namespace_enabled,
    ["kubernetes", "security", "isolation"],
    supported_resource_types=["k8s_workload"],
)
register(
    "k8s.container.run_as_non_root.missing",
    "operational_safety",
    "HIGH",
    "Kubernetes runAsNonRoot missing",
    "Detects containers that do not enforce runAsNonRoot=true.",
    container_run_as_non_root_missing,
    ["kubernetes", "security", "non-root"],
)
register(
    "k8s.container.allow_privilege_escalation.enabled",
    "operational_safety",
    "HIGH",
    "Kubernetes privilege escalation allowed",
    "Detects containers that allow privilege escalation or leave it undefined.",
    container_allow_privilege_escalation_enabled,
    ["kubernetes", "security", "privilege-escalation"],
)
register(
    "k8s.container.read_only_root_filesystem.disabled",
    "operational_safety",
    "MEDIUM",
    "Kubernetes read-only root filesystem disabled",
    "Detects containers without readOnlyRootFilesystem=true.",
    container_read_only_root_filesystem_disabled,
    ["kubernetes", "security", "filesystem"],
)
register(
    "k8s.container.seccomp_profile.missing",
    "operational_safety",
    "MEDIUM",
    "Kubernetes seccomp profile missing",
    "Detects containers without an explicit seccomp profile.",
    container_seccomp_profile_missing,
    ["kubernetes", "security", "seccomp"],
)
