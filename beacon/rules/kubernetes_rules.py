# beacon/rules/kubernetes_rules.py

from beacon.rules.models import finding


WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}


def evaluate_kubernetes_config(data, file):
    findings = []

    docs = data if isinstance(data, list) else [data]

    for doc in docs:
        if not isinstance(doc, dict):
            continue

        kind = doc.get("kind")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "unknown")

        if kind in WORKLOAD_KINDS:
            findings.extend(evaluate_workload(doc, kind, name, file))

    return findings


def evaluate_workload(doc, kind, name, file):
    findings = []

    spec = doc.get("spec", {})
    template = spec.get("template", {})
    pod_spec = template.get("spec", {})
    containers = pod_spec.get("containers", [])

    replicas = spec.get("replicas")

    if kind in {"Deployment", "StatefulSet"} and replicas == 1:
        findings.append(
            finding(
                rule_id="k8s.workload.replicas.single",
                domain="kubernetes",
                category="resiliency",
                severity="HIGH",
                title=f"Kubernetes {kind} '{name}' has only one replica",
                impact="Single replica workloads may become unavailable during pod or node failure.",
                recommendation="Use at least 2 replicas for production services unless this is intentionally singleton.",
                file=file,
                evidence={"kind": kind, "name": name, "replicas": replicas},
                tags=["kubernetes", "availability", "resiliency"],
            )
        )

    for container in containers:
        container_name = container.get("name", "unknown-container")

        resources = container.get("resources", {})
        if "requests" not in resources or "limits" not in resources:
            findings.append(
                finding(
                    rule_id="k8s.workload.resources.missing",
                    domain="kubernetes",
                    category="scalability",
                    severity="HIGH",
                    title=f"Container '{container_name}' in {kind} '{name}' is missing resource requests or limits",
                    impact="Missing resource boundaries can cause noisy-neighbor issues, unstable scheduling, and production saturation.",
                    recommendation="Define CPU/memory requests and limits for production workloads.",
                    file=file,
                    evidence={
                        "kind": kind,
                        "workload": name,
                        "container": container_name,
                        "resources": resources,
                    },
                    tags=["kubernetes", "resources", "scheduling"],
                )
            )

        if "readinessProbe" not in container or "livenessProbe" not in container:
            findings.append(
                finding(
                    rule_id="k8s.workload.probes.missing",
                    domain="kubernetes",
                    category="operational_safety",
                    severity="HIGH",
                    title=f"Container '{container_name}' in {kind} '{name}' is missing readiness or liveness probes",
                    impact="Missing probes can cause bad traffic routing and delayed failure recovery.",
                    recommendation="Define readiness and liveness probes for production workloads.",
                    file=file,
                    evidence={
                        "kind": kind,
                        "workload": name,
                        "container": container_name,
                        "has_readiness_probe": "readinessProbe" in container,
                        "has_liveness_probe": "livenessProbe" in container,
                    },
                    tags=["kubernetes", "health-checks", "recovery"],
                )
            )

        security_context = container.get("securityContext", {})
        if security_context.get("privileged") is True:
            findings.append(
                finding(
                    rule_id="k8s.container.privileged",
                    domain="kubernetes",
                    category="operational_safety",
                    severity="CRITICAL",
                    title=f"Container '{container_name}' in {kind} '{name}' is running privileged",
                    impact="Privileged containers increase cluster blast radius during compromise or misconfiguration.",
                    recommendation="Avoid privileged containers unless explicitly required and approved.",
                    file=file,
                    evidence={
                        "kind": kind,
                        "workload": name,
                        "container": container_name,
                        "privileged": True,
                    },
                    tags=["kubernetes", "security", "privileged"],
                )
            )

        image = container.get("image", "")
        if image.endswith(":latest") or ":" not in image:
            findings.append(
                finding(
                    rule_id="k8s.image.latest_tag",
                    domain="kubernetes",
                    category="operational_safety",
                    severity="MEDIUM",
                    title=f"Container '{container_name}' in {kind} '{name}' uses an unsafe image tag",
                    impact="Mutable image tags make deployments less predictable and rollback harder.",
                    recommendation="Use immutable versioned image tags or digests.",
                    file=file,
                    evidence={
                        "kind": kind,
                        "workload": name,
                        "container": container_name,
                        "image": image,
                    },
                    tags=["kubernetes", "deployment", "rollback"],
                )
            )

    return findings
