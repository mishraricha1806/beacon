import os
import yaml
import hcl2

from beacon.rules import evaluate_kafka_config, evaluate_terraform_config


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
    "reports"
}

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def scan_path(path: str):
    findings = []

    if not os.path.exists(path):
        return [{
            "severity": "ERROR",
            "title": f"Path does not exist: {path}",
            "impact": "Beacon cannot scan a missing path.",
            "recommendation": "Provide a valid file or directory path.",
            "file": path
        }]

    if os.path.isfile(path):
        return scan_file(path)

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(SUPPORTED_EXTENSIONS):
                continue

            full_path = os.path.join(root, file)
            findings.extend(scan_file(full_path))

    return findings


def scan_file(full_path: str):
    findings = []

    try:
        file_size = os.path.getsize(full_path)

        if file_size > MAX_FILE_SIZE_BYTES:
            return [{
                "severity": "LOW",
                "title": f"Skipped large file: {os.path.basename(full_path)}",
                "impact": "Large files can slow down scanning and may not be suitable for lightweight static analysis.",
                "recommendation": "Split large infrastructure files or increase scanner limit intentionally.",
                "file": full_path
            }]

        if full_path.endswith((".yaml", ".yml")):
            with open(full_path, "r") as f:
                data = yaml.safe_load(f) or {}

            findings.extend(evaluate_kafka_config(data, full_path))

        elif full_path.endswith(".tf"):
            with open(full_path, "r") as f:
                data = hcl2.load(f)

            findings.extend(evaluate_terraform_config(data, full_path))

    except Exception as e:
        findings.append({
            "severity": "ERROR",
            "title": f"Failed to parse {os.path.basename(full_path)}",
            "impact": str(e),
            "recommendation": "Check file syntax and ensure it is a valid supported infrastructure file.",
            "file": full_path
        })

    return findings