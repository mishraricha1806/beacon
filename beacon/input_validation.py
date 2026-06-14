from pathlib import Path


def missing_path_finding(path):
    path_string = str(path)
    return {
        "rule_id": "scanner.path.missing",
        "domain": "scanner",
        "category": "operational_safety",
        "severity": "ERROR",
        "title": f"Path does not exist: {path_string}",
        "impact": "Beacon cannot scan a missing path.",
        "recommendation": "Provide a valid file or directory path.",
        "file": path_string,
        "evidence": {"path": path_string},
        "tags": ["scanner", "input-validation"],
    }


def path_missing(path):
    return not Path(path).exists()
