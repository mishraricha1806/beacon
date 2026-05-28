import os

import hcl2
import yaml

import beacon.rules.iam_registered_rules  # noqa: F401
import beacon.rules.kafka_registered_rules  # noqa: F401
import beacon.rules.kubernetes_registered_rules  # noqa: F401
import beacon.rules.storage_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_terraform_config, normalize_yaml_document
from beacon.rules.kafka_rules import evaluate_kafka_config
from beacon.rules.kubernetes_rules import evaluate_kubernetes_config
from beacon.rules.terraform_rules import evaluate_terraform_config


SUPPORTED_EXTENSIONS = (".tf", ".yaml", ".yml")

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

        for file_name in files:
            if not file_name.endswith(SUPPORTED_EXTENSIONS):
                continue

            full_path = os.path.join(root, file_name)
            findings.extend(scan_file(full_path))

    return findings


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

    except Exception as error:
        findings.append(
            scanner_finding(
                rule_id="scanner.file.parse_failed",
                severity="ERROR",
                title=f"Failed to parse {os.path.basename(full_path)}",
                impact=str(error),
                recommendation=(
                    "Check file syntax and ensure it is a valid supported "
                    "infrastructure file."
                ),
                file=full_path,
                evidence={
                    "file": full_path,
                    "error": str(error),
                },
            )
        )

    return findings


def scan_yaml_file(full_path: str):
    findings = []

    with open(full_path, "r") as f:
        documents = list(yaml.safe_load_all(f))

    for data in documents:
        data = data or {}

        if not isinstance(data, dict):
            continue

        resources = normalize_yaml_document(data, full_path)

        if resources:
            findings.extend(
                evaluate(
                    resources,
                    context={"file": full_path},
                )
            )
            continue

        findings.extend(route_unmigrated_yaml_document(data, full_path))

    return findings


def scan_terraform_file(full_path: str):
    with open(full_path, "r") as f:
        data = hcl2.load(f)

    resources = normalize_terraform_config(data, full_path)

    if resources:
        return evaluate(
            resources,
            context={"file": full_path},
        )

    return evaluate_terraform_config(data, full_path)


def route_unmigrated_yaml_document(data, full_path):
    findings = []

    if is_kubernetes_document(data):
        findings.extend(
            evaluate_kubernetes_config(
                data,
                full_path,
            )
        )

    elif is_kafka_document(data):
        findings.extend(
            evaluate_kafka_config(
                data,
                full_path,
            )
        )

    return findings


def is_kubernetes_document(data):
    return isinstance(data, dict) and "kind" in data and "apiVersion" in data


def is_kafka_document(data):
    return isinstance(data, dict) and ("topics" in data or "kafka" in data)
