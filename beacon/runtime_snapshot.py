import logging
import time

import yaml

import beacon.rules.api_runtime_registered_rules  # noqa: F401
import beacon.rules.database_runtime_registered_rules  # noqa: F401
import beacon.rules.flow_registered_rules  # noqa: F401
import beacon.rules.storage_runtime_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import normalize_yaml_document


LOGGER = logging.getLogger(__name__)


def analyze_runtime_snapshot_file(path):
    started = time.monotonic()
    LOGGER.info("runtime_snapshot.start path=%s", path)
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    findings = analyze_runtime_snapshot(data, source=path)
    LOGGER.info(
        "runtime_snapshot.complete path=%s findings=%s elapsed=%.2fs",
        path,
        len(findings),
        time.monotonic() - started,
    )
    return findings


def analyze_runtime_snapshot(data, source="runtime-snapshot"):
    LOGGER.info("runtime_snapshot.normalize source=%s", source)
    resources = normalize_yaml_document(data, source)
    LOGGER.info("runtime_snapshot.evaluate source=%s resources=%s", source, len(resources))
    findings = evaluate(resources, context={"file": source})
    LOGGER.info("runtime_snapshot.evaluated source=%s findings=%s", source, len(findings))
    return findings
