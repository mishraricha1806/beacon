from beacon.engine.models import Resource


def normalize_kubernetes_config(data, source):
    if not isinstance(data, dict):
        return []

    kind = data.get("kind")
    metadata = data.get("metadata", {})
    name = metadata.get("name", "unknown-workload")

    if kind not in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}:
        return []

    spec = data.get("spec", {})
    template = spec.get("template", {})
    pod_spec = template.get("spec", {})
    containers = pod_spec.get("containers", [])
    replicas = spec.get("replicas")

    resources = []

    for container in containers:
        security_context = container.get("securityContext", {})

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
