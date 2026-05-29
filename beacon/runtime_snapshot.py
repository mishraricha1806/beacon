import yaml

import beacon.rules.api_runtime_registered_rules  # noqa: F401
import beacon.rules.database_runtime_registered_rules  # noqa: F401
import beacon.rules.flow_registered_rules  # noqa: F401
import beacon.rules.storage_runtime_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_yaml_document


def analyze_runtime_snapshot_file(path):
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return analyze_runtime_snapshot(data, source=path)


def analyze_runtime_snapshot(data, source="runtime-snapshot"):
    resources = normalize_yaml_document(data, source)

    return evaluate(resources, context={"file": source})
