import os
import json
import shutil
import subprocess

import hcl2
import yaml

import beacon.rules.iam_registered_rules  # noqa: F401
import beacon.rules.api_runtime_registered_rules  # noqa: F401
import beacon.rules.cicd_registered_rules  # noqa: F401
import beacon.rules.cloud_registered_rules  # noqa: F401
import beacon.rules.database_runtime_registered_rules  # noqa: F401
import beacon.rules.flow_registered_rules  # noqa: F401
import beacon.rules.kafka_registered_rules  # noqa: F401
import beacon.rules.kubernetes_registered_rules  # noqa: F401
import beacon.rules.kubernetes_runtime_registered_rules  # noqa: F401
import beacon.rules.storage_runtime_registered_rules  # noqa: F401
import beacon.rules.storage_registered_rules  # noqa: F401
import beacon.rules.topology_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import (
    normalize_terraform_config,
    normalize_terraform_json,
    normalize_yaml_document,
)
from beacon.readiness.correlations import augment_readiness_findings

SUPPORTED_EXTENSIONS = (".tf", ".yaml", ".yml", ".json")

SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "target",
    "build",
    "dist",
    ".terraform",
    ".terragrunt-cache",
    "reports",
}

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024


def scanner_finding(
    rule_id,
    severity,
    title,
    impact,
    recommendation,
    file,
    evidence=None,
):
    return {
        "rule_id": rule_id,
        "domain": "scanner",
        "category": "operational_safety",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence or {},
        "tags": ["scanner", "input-validation"],
    }


def scan_path(path: str):
    findings = []

    if not os.path.exists(path):
        return [
            scanner_finding(
                rule_id="scanner.path.missing",
                severity="ERROR",
                title=f"Path does not exist: {path}",
                impact="Beacon cannot scan a missing path.",
                recommendation="Provide a valid file or directory path.",
                file=path,
                evidence={"path": path},
            )
        ]

    if os.path.isfile(path):
        return scan_file(path)

    for root, dirs, files in os.walk(path):
        dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]

        if "Chart.yaml" in files and "templates" in dirs:
            findings.extend(scan_helm_chart(root))
            dirs[:] = [directory for directory in dirs if directory != "templates"]

        for file_name in files:
            if not file_name.endswith(SUPPORTED_EXTENSIONS):
                continue

            full_path = os.path.join(root, file_name)
            findings.extend(scan_file(full_path))

    return augment_readiness_findings(findings)


def scan_file(full_path: str):
    findings = []

    try:
        file_size = os.path.getsize(full_path)

        if file_size > MAX_FILE_SIZE_BYTES:
            return [
                scanner_finding(
                    rule_id="scanner.file.too_large",
                    severity="LOW",
                    title=f"Skipped large file: {os.path.basename(full_path)}",
                    impact=(
                        "Large files can slow down scanning and may not be suitable "
                        "for lightweight static analysis."
                    ),
                    recommendation=(
                        "Split large infrastructure files or increase scanner limit "
                        "intentionally."
                    ),
                    file=full_path,
                    evidence={
                        "file": full_path,
                        "size_bytes": file_size,
                        "max_size_bytes": MAX_FILE_SIZE_BYTES,
                    },
                )
            ]

        if full_path.endswith((".yaml", ".yml")):
            findings.extend(scan_yaml_file(full_path))

        elif full_path.endswith(".tf"):
            findings.extend(scan_terraform_file(full_path))

        elif full_path.endswith(".json"):
            findings.extend(scan_json_file(full_path))

    except Exception as error:
        findings.append(
            scanner_finding(
                rule_id="scanner.file.parse_failed",
                severity="ERROR",
                title=f"Failed to parse {os.path.basename(full_path)}",
                impact=str(error),
                recommendation=(
                    "Check file syntax and ensure it is a valid supported " "infrastructure file."
                ),
                file=full_path,
                evidence={
                    "file": full_path,
                    "error": str(error),
                },
            )
        )

    return augment_readiness_findings(findings)


def scan_yaml_file(full_path: str):
    resources = []

    with open(full_path, "r") as f:
        documents = list(yaml.safe_load_all(f))

    for data in documents:
        data = data or {}

        if not isinstance(data, dict):
            continue

        resources.extend(normalize_yaml_document(data, full_path))

    if not resources:
        return []

    return evaluate(
        resources,
        context={"file": full_path, "resources": resources},
    )


def scan_terraform_file(full_path: str):
    with open(full_path, "r") as f:
        data = hcl2.load(f)

    resources = normalize_terraform_config(data, full_path)

    if resources:
        return evaluate(
            resources,
            context={"file": full_path, "resources": resources},
        )

    return []


def scan_json_file(full_path: str):
    with open(full_path, "r") as f:
        data = json.load(f)

    resources = normalize_terraform_json(data, full_path)

    if not resources:
        return []

    return evaluate(
        resources,
        context={"file": full_path, "resources": resources},
    )


def scan_helm_chart(chart_path: str):
    helm = shutil.which("helm")

    if not helm:
        return [
            scanner_finding(
                rule_id="helm.render.unavailable",
                severity="ERROR",
                title=f"Helm chart could not be rendered: {os.path.basename(chart_path)}",
                impact="Beacon cannot evaluate Helm templates without rendered Kubernetes manifests.",
                recommendation="Install the helm CLI or provide rendered Kubernetes manifests for scanning.",
                file=chart_path,
                evidence={"chart_path": chart_path, "required_binary": "helm"},
            )
        ]

    try:
        result = subprocess.run(
            [helm, "template", chart_path, "--include-crds"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as error:
        return [
            scanner_finding(
                rule_id="helm.render.failed",
                severity="ERROR",
                title=f"Helm chart render failed: {os.path.basename(chart_path)}",
                impact="Beacon cannot evaluate Helm chart output until it renders successfully.",
                recommendation="Run helm template locally, fix chart rendering errors, and retry Beacon.",
                file=chart_path,
                evidence={"chart_path": chart_path, "error": str(error)},
            )
        ]

    return scan_yaml_documents(
        result.stdout,
        source=f"helm:{chart_path}",
    )


def scan_yaml_documents(content: str, source: str):
    resources = []

    documents = list(yaml.safe_load_all(content))

    for data in documents:
        data = data or {}

        if not isinstance(data, dict):
            continue

        resources.extend(normalize_yaml_document(data, source))

    if not resources:
        return []

    return evaluate(
        resources,
        context={"file": source, "resources": resources},
    )
