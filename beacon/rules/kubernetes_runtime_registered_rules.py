from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_k8s_runtime_finding(
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


def node_not_ready(resource, context):
    if resource.attributes.get("ready") is not False:
        return None

    return build_k8s_runtime_finding(
        resource,
        "k8s.runtime.node.not_ready",
        "resiliency",
        "CRITICAL",
        f"Kubernetes node '{resource.name}' is not Ready",
        "NotReady nodes reduce available capacity and can disrupt workloads during scheduling or failover.",
        "Investigate node health, kubelet status, networking, disk pressure, and recent node changes.",
        {"node": resource.name, "ready": False},
        ["kubernetes", "node", "runtime"],
    )


def node_pressure(resource, context):
    pressure = resource.attributes.get("pressure", [])

    if not pressure:
        return None

    return build_k8s_runtime_finding(
        resource,
        "k8s.runtime.node.pressure",
        "scalability",
        "HIGH",
        f"Kubernetes node '{resource.name}' reports pressure",
        "Node pressure can cause pod evictions, scheduling failures, and degraded workload stability.",
        "Review node CPU, memory, disk, and PID pressure. Add capacity or rebalance workloads.",
        {"node": resource.name, "pressure": pressure},
        ["kubernetes", "node", "capacity"],
    )


def pod_crash_looping(resource, context):
    restart_count = resource.attributes.get("restart_count", 0)
    waiting_reason = resource.attributes.get("waiting_reason")

    if waiting_reason != "CrashLoopBackOff" and restart_count < 5:
        return None

    return build_k8s_runtime_finding(
        resource,
        "k8s.runtime.pod.crash_loop",
        "runtime_stability",
        "HIGH",
        f"Kubernetes pod '{resource.name}' is crash looping",
        "Crash looping pods indicate unstable application startup or runtime failure.",
        "Inspect pod events, container logs, recent deployments, configuration, and dependency availability.",
        {
            "pod": resource.name,
            "namespace": resource.attributes.get("namespace"),
            "restart_count": restart_count,
            "waiting_reason": waiting_reason,
        },
        ["kubernetes", "pod", "runtime"],
    )


def pod_pending(resource, context):
    phase = resource.attributes.get("phase")

    if phase != "Pending":
        return None

    return build_k8s_runtime_finding(
        resource,
        "k8s.runtime.pod.pending",
        "scalability",
        "HIGH",
        f"Kubernetes pod '{resource.name}' is Pending",
        "Pending pods can indicate insufficient cluster capacity, missing volumes, or scheduling constraints.",
        "Review scheduler events, node capacity, affinity rules, taints, tolerations, and persistent volumes.",
        {
            "pod": resource.name,
            "namespace": resource.attributes.get("namespace"),
            "phase": phase,
        },
        ["kubernetes", "pod", "scheduling"],
    )


def deployment_unavailable(resource, context):
    desired = resource.attributes.get("desired_replicas")
    available = resource.attributes.get("available_replicas")

    if desired is None or available is None or available >= desired:
        return None

    severity = "CRITICAL" if available == 0 else "HIGH"

    return build_k8s_runtime_finding(
        resource,
        "k8s.runtime.deployment.unavailable",
        "resiliency",
        severity,
        f"Kubernetes deployment '{resource.name}' has unavailable replicas",
        "Unavailable replicas reduce service capacity and can indicate rollout or runtime failure.",
        "Inspect rollout status, pod events, readiness probes, resource pressure, and recent deployments.",
        {
            "deployment": resource.name,
            "namespace": resource.attributes.get("namespace"),
            "desired_replicas": desired,
            "available_replicas": available,
        },
        ["kubernetes", "deployment", "availability"],
    )


def register(rule_id, resource_type, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="kubernetes",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=[resource_type],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "k8s.runtime.node.not_ready",
    "k8s_runtime_node",
    "resiliency",
    "CRITICAL",
    "Kubernetes node not ready",
    "Detects runtime Kubernetes nodes that are not Ready.",
    node_not_ready,
    ["kubernetes", "node", "runtime"],
)

register(
    "k8s.runtime.node.pressure",
    "k8s_runtime_node",
    "scalability",
    "HIGH",
    "Kubernetes node pressure",
    "Detects runtime Kubernetes nodes reporting pressure.",
    node_pressure,
    ["kubernetes", "node", "capacity"],
)

register(
    "k8s.runtime.pod.crash_loop",
    "k8s_runtime_pod",
    "runtime_stability",
    "HIGH",
    "Kubernetes pod crash loop",
    "Detects pods with CrashLoopBackOff or high restart count.",
    pod_crash_looping,
    ["kubernetes", "pod", "runtime"],
)

register(
    "k8s.runtime.pod.pending",
    "k8s_runtime_pod",
    "scalability",
    "HIGH",
    "Kubernetes pod pending",
    "Detects pods stuck in Pending phase.",
    pod_pending,
    ["kubernetes", "pod", "scheduling"],
)

register(
    "k8s.runtime.deployment.unavailable",
    "k8s_runtime_deployment",
    "resiliency",
    "HIGH",
    "Kubernetes deployment unavailable",
    "Detects deployments with unavailable replicas.",
    deployment_unavailable,
    ["kubernetes", "deployment", "availability"],
)
