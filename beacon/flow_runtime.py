import logging
import time

import yaml

import beacon.rules.flow_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_flow_runtime
from beacon.input_validation import missing_path_finding, path_missing

LOGGER = logging.getLogger(__name__)


def analyze_flow_file(path):
    started = time.monotonic()
    LOGGER.info("flow_runtime.start path=%s", path)
    if path_missing(path):
        LOGGER.warning("flow_runtime.path_missing path=%s", path)
        return [missing_path_finding(path)]

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    flow_data = data.get("flow_runtime", data)
    LOGGER.info(
        "flow_runtime.normalize path=%s flow=%s",
        path,
        flow_data.get("name") if isinstance(flow_data, dict) else "unknown",
    )
    resources = normalize_flow_runtime(flow_data, path)
    LOGGER.info("flow_runtime.evaluate path=%s resources=%s", path, len(resources))

    findings = evaluate(resources, context={"file": path})
    LOGGER.info(
        "flow_runtime.complete path=%s findings=%s elapsed=%.2fs",
        path,
        len(findings),
        time.monotonic() - started,
    )
    return findings
