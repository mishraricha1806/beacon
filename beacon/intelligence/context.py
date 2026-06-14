import fnmatch
import json
import os
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONTEXT_PATH = os.path.expanduser("~/.beacon/context.yaml")


def load_intelligence_context(path: Optional[str] = None) -> Dict[str, Any]:
    """Load deterministic organization context used to interpret findings.

    This is intentionally not an AI/RAG execution path. It is structured context
    that can explain and adjust deterministic findings in a repeatable way.
    """

    context_path = (
        path or os.environ.get("BEACON_INTELLIGENCE_CONTEXT_FILE") or DEFAULT_CONTEXT_PATH
    )

    if not context_path or not isinstance(context_path, (str, bytes, os.PathLike)):
        return {}

    if not os.path.exists(context_path):
        return {}

    try:
        with open(context_path, "r") as f:
            if context_path.endswith(".json"):
                data = json.load(f)
            else:
                data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def context_environment(context: Optional[Dict[str, Any]]) -> Optional[str]:
    if not context:
        return None

    organization = context.get("organization") or {}
    environment = (
        context.get("environment") or organization.get("environment") or context.get("profile")
    )
    return environment if isinstance(environment, str) and environment else None


def context_summary(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {"loaded": False}

    organization = context.get("organization") or {}
    return {
        "loaded": True,
        "organization": organization.get("name") or context.get("organization_name"),
        "environment": context_environment(context),
        "rule_overrides": len(context.get("rule_overrides") or {}),
        "topic_patterns": len(context.get("topic_patterns") or {}),
        "knowledge_documents": len(context.get("knowledge_documents") or []),
    }


def rule_context_override(
    context: Optional[Dict[str, Any]], rule_id: str, environment: str
) -> Dict[str, Any]:
    if not context or not rule_id:
        return {}

    overrides = context.get("rule_overrides") or {}
    override = overrides.get(rule_id) or {}

    environment_overrides = (
        (context.get("environments") or {}).get(environment, {}).get("rule_overrides", {})
    )
    environment_override = environment_overrides.get(rule_id) or {}

    merged = dict(override)
    merged.update(environment_override)
    return merged


def kafka_environment_policy(context: Optional[Dict[str, Any]], environment: str) -> Dict[str, Any]:
    if not context:
        return {}

    environments = context.get("environments") or {}
    policy = dict((environments.get(environment) or {}).get("kafka") or {})

    kafka_policy = context.get("kafka_policy") or {}
    policy.update(kafka_policy.get(environment) or {})

    return policy


def topic_context(context: Optional[Dict[str, Any]], topic: Optional[str]) -> Dict[str, Any]:
    if not context or not topic:
        return {}

    matched = {}
    for pattern, settings in (context.get("topic_patterns") or {}).items():
        if fnmatch.fnmatch(topic, pattern) and isinstance(settings, dict):
            matched.update(settings)

    return matched
