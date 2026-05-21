import os
import yaml
import hcl2

from beacon.rules import evaluate_kafka_config, evaluate_terraform_config


def scan_path(path: str):
    findings = []

    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)

            try:
                if file.endswith((".yaml", ".yml")):
                    with open(full_path, "r") as f:
                        data = yaml.safe_load(f) or {}
                        findings.extend(evaluate_kafka_config(data, full_path))

                elif file.endswith(".tf"):
                    with open(full_path, "r") as f:
                        data = hcl2.load(f)
                        findings.extend(evaluate_terraform_config(data, full_path))

            except Exception as e:
                findings.append({
                    "severity": "ERROR",
                    "title": f"Failed to parse {file}",
                    "impact": str(e),
                    "recommendation": "Check file syntax.",
                    "file": full_path
                })

    return findings
