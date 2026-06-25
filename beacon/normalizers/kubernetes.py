from beacon.engine.models import Resource


def normalize_kubernetes_config(data, source):
    if not isinstance(data, dict):
        return []

    kind = data.get("kind")
    metadata = data.get("metadata", {})
    name = metadata.get("name", "unknown-workload")
    namespace = metadata.get("namespace", "default")

    if kind == "Namespace":
        labels = metadata.get("labels", {}) or {}
        return [
            Resource(
                type="k8s_namespace",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "labels": labels,
                    "pod_security_enforce": labels.get("pod-security.kubernetes.io/enforce"),
                    "pod_security_audit": labels.get("pod-security.kubernetes.io/audit"),
                    "pod_security_warn": labels.get("pod-security.kubernetes.io/warn"),
                },
            )
        ]

    if kind in {"Role", "ClusterRole"}:
        return [
            Resource(
                type="k8s_rbac_role",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "namespace": namespace if kind == "Role" else None,
                    "rules": data.get("rules", []),
                },
            )
        ]

    if kind in {"RoleBinding", "ClusterRoleBinding"}:
        role_ref = data.get("roleRef", {}) or {}
        return [
            Resource(
                type="k8s_rbac_binding",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "namespace": namespace if kind == "RoleBinding" else None,
                    "role_ref_kind": role_ref.get("kind"),
                    "role_ref_name": role_ref.get("name"),
                    "subjects": data.get("subjects", []),
                },
            )
        ]

    if kind in {"ValidatingWebhookConfiguration", "MutatingWebhookConfiguration"}:
        return [
            Resource(
                type="k8s_admission_webhook",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "webhooks": data.get("webhooks", []),
                },
            )
        ]

    if kind == "Secret":
        return [
            Resource(
                type="k8s_secret",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": namespace,
                    "secret_type": data.get("type"),
                    "data_keys": sorted((data.get("data") or {}).keys()),
                    "string_data_keys": sorted((data.get("stringData") or {}).keys()),
                },
            )
        ]

    if kind in {"ExternalSecret", "SecretStore", "ClusterSecretStore"}:
        return [
            Resource(
                type="k8s_external_secret",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "namespace": namespace if kind != "ClusterSecretStore" else None,
                },
            )
        ]

    if kind == "PodDisruptionBudget":
        spec = data.get("spec", {})
        return [
            Resource(
                type="k8s_pod_disruption_budget",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": namespace,
                    "selector_labels": (spec.get("selector") or {}).get("matchLabels", {}),
                    "min_available": spec.get("minAvailable"),
                    "max_unavailable": spec.get("maxUnavailable"),
                },
            )
        ]

    if kind == "NetworkPolicy":
        spec = data.get("spec", {})
        return [
            Resource(
                type="k8s_network_policy",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": namespace,
                    "pod_selector": spec.get("podSelector", {}).get("matchLabels", {}),
                    "policy_types": spec.get("policyTypes", []),
                    "ingress": spec.get("ingress", []),
                    "egress": spec.get("egress", []),
                },
            )
        ]

    if kind == "HorizontalPodAutoscaler":
        spec = data.get("spec", {})
        scale_target = spec.get("scaleTargetRef", {}) or {}
        return [
            Resource(
                type="k8s_horizontal_pod_autoscaler",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": namespace,
                    "target_kind": scale_target.get("kind"),
                    "target_name": scale_target.get("name"),
                    "min_replicas": spec.get("minReplicas"),
                    "max_replicas": spec.get("maxReplicas"),
                    "metrics": spec.get("metrics", []),
                },
            )
        ]

    if kind not in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}:
        return []

    spec = data.get("spec", {})
    template = spec.get("template", {})
    template_metadata = template.get("metadata", {})
    pod_spec = template.get("spec", {})
    containers = pod_spec.get("containers", [])
    replicas = spec.get("replicas")
    affinity = pod_spec.get("affinity", {}) or {}
    pod_anti_affinity = affinity.get("podAntiAffinity") or {}
    topology_spread_constraints = pod_spec.get("topologySpreadConstraints") or []
    labels = template_metadata.get("labels", {}) or metadata.get("labels", {}) or {}

    resources = []

    resources.append(
        Resource(
            type="k8s_workload",
            name=name,
            domain="kubernetes",
            source=source,
            attributes={
                "kind": kind,
                "namespace": namespace,
                "replicas": replicas,
                "labels": labels,
                "has_topology_spread_constraints": bool(topology_spread_constraints),
                "has_pod_anti_affinity": bool(pod_anti_affinity),
                "service_account_name": pod_spec.get("serviceAccountName"),
                "automount_service_account_token": pod_spec.get("automountServiceAccountToken"),
                "host_network": pod_spec.get("hostNetwork"),
                "host_pid": pod_spec.get("hostPID"),
                "host_ipc": pod_spec.get("hostIPC"),
            },
        )
    )

    for container in containers:
        security_context = container.get("securityContext", {})
        seccomp_profile = security_context.get("seccompProfile") or pod_spec.get(
            "securityContext", {}
        ).get("seccompProfile")
        capabilities = security_context.get("capabilities", {})

        resources.append(
            Resource(
                type="k8s_workload_container",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "replicas": replicas,
                    "container": container.get("name", "unknown-container"),
                    "image": container.get("image", ""),
                    "resources": container.get("resources", {}),
                    "has_readiness_probe": "readinessProbe" in container,
                    "has_liveness_probe": "livenessProbe" in container,
                    "privileged": security_context.get("privileged"),
                    "run_as_non_root": security_context.get("runAsNonRoot"),
                    "allow_privilege_escalation": security_context.get("allowPrivilegeEscalation"),
                    "read_only_root_filesystem": security_context.get("readOnlyRootFilesystem"),
                    "seccomp_profile": seccomp_profile,
                    "capabilities_drop": capabilities.get("drop", []),
                    "host_network": pod_spec.get("hostNetwork"),
                    "host_pid": pod_spec.get("hostPID"),
                    "host_ipc": pod_spec.get("hostIPC"),
                },
            )
        )

    return resources


def normalize_kubernetes_runtime(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for node in data.get("nodes", []):
        pressure = []

        for key in ("memory_pressure", "disk_pressure", "pid_pressure"):
            if node.get(key) is True:
                pressure.append(key)

        resources.append(
            Resource(
                type="k8s_runtime_node",
                name=node.get("name", "unknown-node"),
                domain="kubernetes",
                source=source,
                attributes={
                    "ready": node.get("ready"),
                    "pressure": pressure,
                },
            )
        )

    for pod in data.get("pods", []):
        resources.append(
            Resource(
                type="k8s_runtime_pod",
                name=pod.get("name", "unknown-pod"),
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": pod.get("namespace"),
                    "phase": pod.get("phase"),
                    "restart_count": pod.get("restart_count", 0),
                    "waiting_reason": pod.get("waiting_reason"),
                },
            )
        )

    for deployment in data.get("deployments", []):
        resources.append(
            Resource(
                type="k8s_runtime_deployment",
                name=deployment.get("name", "unknown-deployment"),
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": deployment.get("namespace"),
                    "desired_replicas": deployment.get("desired_replicas"),
                    "available_replicas": deployment.get("available_replicas"),
                },
            )
        )

    return resources
