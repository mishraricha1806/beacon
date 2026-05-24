# Add a rules registry loader that loads built-in metadata and optional YAML overrides from BEACON_RULES_METADATA_DIR or package rules/metadata dir.

import os
import glob
import yaml
from typing import Dict, Any

from beacon import rules_metadata as builtin_metadata


_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _load_from_dir(path: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}

    if not os.path.isdir(path):
        return out

    for p in glob.glob(os.path.join(path, "*.yml")) + glob.glob(os.path.join(path, "*.yaml")):
        try:
            with open(p, "r") as f:
                data = yaml.safe_load(f) or {}

            # allow single rule file or list/dict
            if isinstance(data, dict) and "rule_id" in data:
                out[data["rule_id"]] = data
            elif isinstance(data, dict):
                # if file contains multiple rules as mapping
                for k, v in data.items():
                    if isinstance(v, dict):
                        out[k] = v
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "rule_id" in item:
                        out[item["rule_id"]] = item
        except Exception:
            # ignore malformed metadata files
            continue

    return out


def _load_registry() -> Dict[str, Dict[str, Any]]:
    # Prefer package-level YAML metadata as canonical builtins
    registry: Dict[str, Dict[str, Any]] = {}

    package_dir = os.path.join(os.path.dirname(__file__), "rules", "metadata")
    registry.update(_load_from_dir(package_dir))

    # allow overriding/augmentation via env var pointing to a directory of yaml files
    override_dir = os.environ.get("BEACON_RULES_METADATA_DIR")
    if override_dir:
        registry.update(_load_from_dir(override_dir))

    # fallback to builtin python metadata for any missing rules
    builtin = dict(getattr(builtin_metadata, "RULES", {}))
    for k, v in builtin.items():
        if k not in registry:
            registry[k] = v

    return registry


def reload():
    global _REGISTRY
    _REGISTRY = _load_registry()


def get(rule_id: str) -> Dict[str, Any]:
    if not _REGISTRY:
        reload()
    return _REGISTRY.get(rule_id)


def list_rules() -> Dict[str, Dict[str, Any]]:
    if not _REGISTRY:
        reload()
    return dict(_REGISTRY)
