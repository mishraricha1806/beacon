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


def parse_int_or_percent(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            try:
                return {"percent": int(stripped[:-1])}
            except ValueError:
                return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def unavailable_count(value, replicas):
    parsed = parse_int_or_percent(value)
    if parsed is None:
        return None
    if isinstance(parsed, dict) and "percent" in parsed:
        return max(1, int((replicas * parsed["percent"] + 99) / 100))
    return parsed


def workload_pdb_allows_full_disruption(resource, context):
    replicas = resource.attributes.get("replicas")
    labels = resource.attributes.get("labels") or {}

    if replicas is None or replicas < 2 or not labels:
        return None

    namespace = resource.attributes.get("namespace")
    matching_budgets = [
        item
        for item in context.get("resources", [])
        if item.type == "k8s_pod_disruption_budget"
        and item.attributes.get("namespace") == namespace
        and selector_matches_labels(item.attributes.get("selector_labels"), labels)
    ]

    for budget in matching_budgets:
        min_available = budget.attributes.get("min_available")
        max_unavailable = budget.attributes.get("max_unavailable")
        min_available_count = unavailable_count(min_available, replicas)
        max_unavailable_count = unavailable_count(max_unavailable, replicas)

        if min_available_count == 0 or (
            max_unavailable_count is not None and max_unavailable_count >= replicas
        ):
            return build_k8s_finding(
                resource,
                "k8s.workload.pod_disruption_budget.unsafe",
                "recovery_readiness",
                "HIGH",
                f"Kubernetes workload '{resource.name}' has an unsafe PodDisruptionBudget",
                "A PodDisruptionBudget that allows all replicas to be disrupted does not protect availability during node drains, upgrades, or maintenance.",
                "Set minAvailable to at least 1 or maxUnavailable below total replicas for production workloads.",
                {
                    "workload": resource.name,
                    "namespace": namespace,
                    "replicas": replicas,
                    "pdb": budget.name,
                    "min_available": min_available,
                    "max_unavailable": max_unavailable,
                },
                ["kubernetes", "availability", "pdb", "maintenance"],
            )

    return None


def hpa_scale_headroom_missing(resource, context):
    max_replicas = resource.attributes.get("max_replicas")
    min_replicas = resource.attributes.get("min_replicas")
    target_name = resource.attributes.get("target_name")

    if max_replicas is None:
        return None

    workloads = [
        item
        for item in context.get("resources", [])
        if item.type == "k8s_workload"
        and item.name == target_name
        and item.attributes.get("namespace") == resource.attributes.get("namespace")
    ]
    desired_replicas = workloads[0].attributes.get("replicas") if workloads else min_replicas

    if desired_replicas is None or max_replicas > desired_replicas:
        return None

    return build_k8s_finding(
        resource,
        "k8s.hpa.scale_headroom.missing",
        "scalability",
        "HIGH",
        f"HorizontalPodAutoscaler '{resource.name}' has no scale-out headroom",
        "An HPA with maxReplicas at or below the current replica target cannot absorb traffic spikes automatically.",
        "Set maxReplicas above the steady-state replica count and validate node capacity for the peak target.",
        {
            "hpa": resource.name,
            "target_name": target_name,
            "min_replicas": min_replicas,
            "max_replicas": max_replicas,
            "desired_replicas": desired_replicas,
        },
        ["kubernetes", "autoscaling", "capacity"],
    )


def namespace_pod_security_enforce_missing(resource, context):
    enforce = resource.attributes.get("pod_security_enforce")

    if enforce in {"baseline", "restricted"}:
        return None

    severity = "CRITICAL" if enforce == "privileged" else "HIGH"
    return build_k8s_finding(
        resource,
        "k8s.namespace.pod_security.enforce_missing",
        "operational_safety",
        severity,
        f"Kubernetes namespace '{resource.name}' does not enforce Pod Security Standards",
        "Without namespace-level Pod Security admission, privileged or weakly isolated pods can bypass workload expectations and expand cluster blast radius.",
        "Set pod-security.kubernetes.io/enforce to baseline or restricted, and use audit/warn labels during rollout.",
        {
            "namespace": resource.name,
            "pod_security_enforce": enforce,
            "pod_security_audit": resource.attributes.get("pod_security_audit"),
            "pod_security_warn": resource.attributes.get("pod_security_warn"),
        },
        ["kubernetes", "security", "pod-security", "admission"],
    )


def rbac_role_wildcard_permissions(resource, context):
    offending_rules = []
    for index, rule in enumerate(resource.attributes.get("rules") or []):
        verbs = rule.get("verbs") or []
        resources = rule.get("resources") or []
        api_groups = rule.get("apiGroups") or []

        if "*" in verbs or "*" in resources or "*" in api_groups:
            offending_rules.append(
                {
                    "index": index,
                    "apiGroups": api_groups,
                    "resources": resources,
                    "verbs": verbs,
                }
            )

    if not offending_rules:
        return None

    return build_k8s_finding(
        resource,
        "k8s.rbac.role.wildcard_permissions",
        "operational_safety",
        "HIGH",
        f"Kubernetes {resource.attributes.get('kind')} '{resource.name}' uses wildcard permissions",
        "Wildcard RBAC permissions make privilege boundaries harder to reason about and can grant unintended access as APIs or resources change.",
        "Replace wildcard verbs, resources, and API groups with the minimum permissions required by the workload or operator.",
        {
            "role": resource.name,
            "kind": resource.attributes.get("kind"),
            "namespace": resource.attributes.get("namespace"),
            "offending_rules": offending_rules,
        },
        ["kubernetes", "security", "rbac", "least-privilege"],
    )


def rbac_cluster_admin_broad_binding(resource, context):
    if resource.attributes.get("role_ref_name") != "cluster-admin":
        return None

    subjects = resource.attributes.get("subjects") or []
    broad_subjects = []
    for subject in subjects:
        kind = subject.get("kind")
        name = subject.get("name")
        namespace = subject.get("namespace")
        if kind == "Group" and name in {
            "system:authenticated",
            "system:unauthenticated",
            "system:anonymous",
        }:
            broad_subjects.append(subject)
        if kind == "ServiceAccount" and name == "default":
            broad_subjects.append(subject)
        if kind == "User" and name in {"system:anonymous"}:
            broad_subjects.append(subject)
        if kind == "Group" and name == "system:masters":
            broad_subjects.append(subject)
        if kind == "ServiceAccount" and not namespace:
            broad_subjects.append(subject)

    if not broad_subjects:
        return None

    return build_k8s_finding(
        resource,
        "k8s.rbac.cluster_admin.broad_binding",
        "operational_safety",
        "CRITICAL",
        f"Kubernetes binding '{resource.name}' grants cluster-admin broadly",
        "Broad cluster-admin bindings can give excessive control over workloads, secrets, nodes, and admission policy across the cluster.",
        "Bind cluster-admin only to tightly controlled break-glass identities and use scoped roles for normal operations.",
        {
            "binding": resource.name,
            "kind": resource.attributes.get("kind"),
            "role_ref_name": resource.attributes.get("role_ref_name"),
            "subjects": broad_subjects,
        },
        ["kubernetes", "security", "rbac", "least-privilege"],
    )


def admission_webhook_permissive_failure_policy(resource, context):
    offenders = []
    for webhook in resource.attributes.get("webhooks") or []:
        failure_policy = webhook.get("failurePolicy")
        namespace_selector = webhook.get("namespaceSelector")
        rules = webhook.get("rules") or []
        has_global_scope = namespace_selector in (None, {})

        if failure_policy == "Ignore" and has_global_scope:
            offenders.append(
                {
                    "name": webhook.get("name"),
                    "failurePolicy": failure_policy,
                    "namespaceSelector": namespace_selector,
                    "rules": rules,
                }
            )

    if not offenders:
        return None

    return build_k8s_finding(
        resource,
        "k8s.admission_webhook.failure_policy.ignore",
        "operational_safety",
        "HIGH",
        f"Admission webhook configuration '{resource.name}' can fail open",
        "A globally scoped admission webhook with failurePolicy=Ignore can silently bypass policy enforcement during webhook outages or TLS/configuration failures.",
        "Use failurePolicy=Fail for security-enforcing admission controls, narrow namespace/object selectors, and monitor webhook availability.",
        {
            "webhook_configuration": resource.name,
            "kind": resource.attributes.get("kind"),
            "offending_webhooks": offenders,
        },
        ["kubernetes", "security", "admission", "webhook"],
    )


def inline_secret_material_present(resource, context):
    data_keys = resource.attributes.get("data_keys") or []
    string_data_keys = resource.attributes.get("string_data_keys") or []

    if not data_keys and not string_data_keys:
        return None

    return build_k8s_finding(
        resource,
        "k8s.secret.inline_material",
        "operational_safety",
        "MEDIUM",
        f"Kubernetes Secret '{resource.name}' stores inline secret material",
        "Raw Kubernetes Secrets in manifests can leak through Git history, CI logs, artifact stores, or broad cluster read permissions.",
        "Use an external secret manager integration such as External Secrets Operator, CSI Secret Store, or sealed/encrypted secret workflow approved by the platform team.",
        {
            "secret": resource.name,
            "namespace": resource.attributes.get("namespace"),
            "secret_type": resource.attributes.get("secret_type"),
            "data_keys": data_keys,
            "string_data_keys": string_data_keys,
        },
        ["kubernetes", "security", "secrets"],
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
    "k8s.workload.pod_disruption_budget.unsafe",
    "recovery_readiness",
    "HIGH",
    "Kubernetes PodDisruptionBudget unsafe",
    "Detects PodDisruptionBudgets that allow all replicas to be disrupted.",
    workload_pdb_allows_full_disruption,
    ["kubernetes", "availability", "pdb", "maintenance"],
    supported_resource_types=["k8s_workload"],
)
register(
    "k8s.hpa.scale_headroom.missing",
    "scalability",
    "HIGH",
    "Kubernetes HPA scale headroom missing",
    "Detects HPAs whose maxReplicas cannot scale beyond the current workload replica target.",
    hpa_scale_headroom_missing,
    ["kubernetes", "autoscaling", "capacity"],
    supported_resource_types=["k8s_horizontal_pod_autoscaler"],
)
register(
    "k8s.namespace.pod_security.enforce_missing",
    "operational_safety",
    "HIGH",
    "Kubernetes namespace Pod Security enforcement missing",
    "Detects namespaces without baseline or restricted Pod Security admission enforcement.",
    namespace_pod_security_enforce_missing,
    ["kubernetes", "security", "pod-security", "admission"],
    supported_resource_types=["k8s_namespace"],
)
register(
    "k8s.rbac.role.wildcard_permissions",
    "operational_safety",
    "HIGH",
    "Kubernetes RBAC wildcard permissions",
    "Detects Roles or ClusterRoles with wildcard verbs, resources, or API groups.",
    rbac_role_wildcard_permissions,
    ["kubernetes", "security", "rbac", "least-privilege"],
    supported_resource_types=["k8s_rbac_role"],
)
register(
    "k8s.rbac.cluster_admin.broad_binding",
    "operational_safety",
    "CRITICAL",
    "Kubernetes broad cluster-admin binding",
    "Detects broad or risky ClusterRoleBindings to cluster-admin.",
    rbac_cluster_admin_broad_binding,
    ["kubernetes", "security", "rbac", "least-privilege"],
    supported_resource_types=["k8s_rbac_binding"],
)
register(
    "k8s.admission_webhook.failure_policy.ignore",
    "operational_safety",
    "HIGH",
    "Kubernetes admission webhook fails open",
    "Detects globally scoped admission webhooks using failurePolicy=Ignore.",
    admission_webhook_permissive_failure_policy,
    ["kubernetes", "security", "admission", "webhook"],
    supported_resource_types=["k8s_admission_webhook"],
)
register(
    "k8s.secret.inline_material",
    "operational_safety",
    "MEDIUM",
    "Kubernetes inline Secret material",
    "Detects Kubernetes Secret manifests that contain inline data or stringData.",
    inline_secret_material_present,
    ["kubernetes", "security", "secrets"],
    supported_resource_types=["k8s_secret"],
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
