"""Static readiness evaluators backed by registered rules."""

import beacon.rules.iam_registered_rules  # noqa: F401
import beacon.rules.kafka_registered_rules  # noqa: F401
import beacon.rules.kubernetes_registered_rules  # noqa: F401
import beacon.rules.storage_registered_rules  # noqa: F401
from beacon.engine.evaluator import evaluate
from beacon.engine.normalizer import (
    normalize_kafka_config,
    normalize_terraform_config,
    normalize_yaml_document,
)


def evaluate_kafka_config(data, file):
    return evaluate(
        normalize_kafka_config(data, file),
        context={"file": file},
    )


def evaluate_terraform_config(data, file):
    return evaluate(
        normalize_terraform_config(data, file),
        context={"file": file},
    )


def evaluate_yaml_document(data, file):
    return evaluate(
        normalize_yaml_document(data, file),
        context={"file": file},
    )


__all__ = [
    "evaluate_kafka_config",
    "evaluate_terraform_config",
    "evaluate_yaml_document",
]
