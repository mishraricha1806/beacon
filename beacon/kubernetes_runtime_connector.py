import json
import logging
import shutil
import subprocess
import time

import beacon.rules.kubernetes_runtime_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_kubernetes_runtime


LOGGER = logging.getLogger(__name__)


def finding(
    severity,
    title,
    impact,
    recommendation,
    file="runtime-kubernetes",
    rule_id="k8s.runtime.diagnostic",
    domain="kubernetes",
    category="runtime_stability",
    evidence=None,
    tags=None,
    confidence=None,
):
    result = {
        "rule_id": rule_id,
        "domain": domain,
        "category": category,
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence or {},
        "tags": tags or [],
    }

    if confidence:
        result["confidence"] = confidence

    return result


def analyze_kubernetes_cluster(namespace=None, context=None, kubeconfig=None):
    started = time.monotonic()
    LOGGER.info(
        "kubernetes.start namespace=%s context=%s kubeconfig=%s",
        namespace,
        context,
        bool(kubeconfig),
    )
    findings = [
        finding(
            "INFO",
            "Beacon Kubernetes connector is running in read-only diagnostic mode",
            "Beacon will only collect Kubernetes status and metadata signals for analysis.",
            "No Kubernetes mutation operation will be performed.",
            rule_id="k8s.runtime.read_only_mode",
            evidence={"mode": "read_only", "mutation_allowed": False},
            confidence="HIGH",
        )
    ]

    kubectl = shutil.which("kubectl")

    if not kubectl:
        LOGGER.warning("kubernetes.kubectl_missing")
        findings.append(
            finding(
                "ERROR",
                "kubectl is not available for Kubernetes runtime readiness",
                "Beacon cannot collect live Kubernetes runtime signals without kubectl.",
                "Install kubectl or provide a Kubernetes runtime snapshot YAML.",
                rule_id="k8s.runtime.kubectl.unavailable",
                evidence={"required_binary": "kubectl"},
                confidence="HIGH",
            )
        )
        return findings

    try:
        LOGGER.info("kubernetes.collect.start kubectl=%s", kubectl)
        snapshot = collect_kubernetes_snapshot(
            kubectl=kubectl,
            namespace=namespace,
            context=context,
            kubeconfig=kubeconfig,
        )
    except Exception as error:
        LOGGER.info("kubernetes.collect.failed error=%s", error, exc_info=True)
        findings.append(
            finding(
                "ERROR",
                "Kubernetes runtime collection failed",
                "Beacon could not collect Kubernetes runtime status.",
                "Check kubectl access, kubeconfig, context, namespace, and cluster API availability.",
                rule_id="k8s.runtime.collection.failed",
                evidence={
                    "namespace": namespace,
                    "context": context,
                    "kubeconfig_configured": bool(kubeconfig),
                    "error": str(error),
                },
                confidence="HIGH",
            )
        )
        return findings

    LOGGER.info(
        "kubernetes.collect.complete nodes=%s pods=%s deployments=%s",
        len(snapshot.get("nodes", [])),
        len(snapshot.get("pods", [])),
        len(snapshot.get("deployments", [])),
    )
    findings.append(
        finding(
            "LOW",
            "Kubernetes runtime collection successful",
            "Beacon collected Kubernetes runtime status using read-only kubectl get commands.",
            "No action required.",
            rule_id="k8s.runtime.collection.success",
            evidence={
                "namespace": namespace,
                "context": context,
                "nodes": len(snapshot.get("nodes", [])),
                "pods": len(snapshot.get("pods", [])),
                "deployments": len(snapshot.get("deployments", [])),
            },
            confidence="HIGH",
        )
    )

    resources = normalize_kubernetes_runtime(snapshot, "runtime-kubernetes")
    LOGGER.info("kubernetes.evaluate resources=%s", len(resources))

    findings.extend(evaluate(resources, context={"file": "runtime-kubernetes"}))
    LOGGER.info(
        "kubernetes.complete findings=%s elapsed=%.2fs",
        len(findings),
        time.monotonic() - started,
    )

    return findings


def collect_kubernetes_snapshot(kubectl, namespace=None, context=None, kubeconfig=None):
    nodes_payload = run_kubectl_json(
        kubectl,
        ["get", "nodes", "-o", "json"],
        context=context,
        kubeconfig=kubeconfig,
    )

    scope = ["-A"] if namespace is None else ["-n", namespace]

    pods_payload = run_kubectl_json(
        kubectl,
        ["get", "pods", *scope, "-o", "json"],
        context=context,
        kubeconfig=kubeconfig,
    )

    deployments_payload = run_kubectl_json(
        kubectl,
        ["get", "deployments", *scope, "-o", "json"],
        context=context,
        kubeconfig=kubeconfig,
    )

    return {
        "nodes": parse_nodes(nodes_payload),
        "pods": parse_pods(pods_payload),
        "deployments": parse_deployments(deployments_payload),
    }


def run_kubectl_json(kubectl, args, context=None, kubeconfig=None):
    command = [kubectl]

    if context:
        command.extend(["--context", context])

    if kubeconfig:
        command.extend(["--kubeconfig", kubeconfig])

    command.extend(args)
    started = time.monotonic()
    LOGGER.info("kubernetes.kubectl.start args=%s", " ".join(args))

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        LOGGER.info(
            "kubernetes.kubectl.elapsed args=%s seconds=%.2f",
            " ".join(args),
            time.monotonic() - started,
        )

    return json.loads(result.stdout)


def parse_nodes(payload):
    nodes = []

    for item in payload.get("items", []):
        conditions = {
            condition.get("type"): condition.get("status")
            for condition in item.get("status", {}).get("conditions", [])
        }

        nodes.append(
            {
                "name": item.get("metadata", {}).get("name"),
                "ready": conditions.get("Ready") == "True",
                "memory_pressure": conditions.get("MemoryPressure") == "True",
                "disk_pressure": conditions.get("DiskPressure") == "True",
                "pid_pressure": conditions.get("PIDPressure") == "True",
            }
        )

    return nodes


def parse_pods(payload):
    pods = []

    for item in payload.get("items", []):
        statuses = item.get("status", {}).get("containerStatuses", []) or []
        restart_count = sum(status.get("restartCount", 0) for status in statuses)
        waiting_reason = None

        for status in statuses:
            waiting = status.get("state", {}).get("waiting")

            if waiting:
                waiting_reason = waiting.get("reason")
                break

        pods.append(
            {
                "name": item.get("metadata", {}).get("name"),
                "namespace": item.get("metadata", {}).get("namespace"),
                "phase": item.get("status", {}).get("phase"),
                "restart_count": restart_count,
                "waiting_reason": waiting_reason,
            }
        )

    return pods


def parse_deployments(payload):
    deployments = []

    for item in payload.get("items", []):
        deployments.append(
            {
                "name": item.get("metadata", {}).get("name"),
                "namespace": item.get("metadata", {}).get("namespace"),
                "desired_replicas": item.get("spec", {}).get("replicas", 1),
                "available_replicas": item.get("status", {}).get(
                    "availableReplicas", 0
                ),
            }
        )

    return deployments
