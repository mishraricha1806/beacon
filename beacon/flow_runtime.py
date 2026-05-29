import yaml

import beacon.rules.flow_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_flow_runtime


def analyze_flow_file(path):
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    flow_data = data.get("flow_runtime", data)
    resources = normalize_flow_runtime(flow_data, path)

    return evaluate(resources, context={"file": path})
