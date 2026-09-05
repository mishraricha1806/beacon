"""Inspectable readiness pack catalog.

Packs are not a second rule engine. They are a public, reviewable layer that
groups Beacon's deterministic rule IDs into product-ready readiness domains.
"""

import os
import sys
from pathlib import Path

import yaml

from beacon.contracts import engine_metadata
from beacon.engine import metadata_registry

PACK_FILENAMES = ("pack.yaml", "pack.yml")
PACK_SCHEMA_VERSION = "1.0.0"
PACK_STATUSES = {"preview", "stable", "deprecated"}
PACK_SUPPORT_TIERS = {"experimental", "supported", "critical"}
PACK_REQUIRED_FIELDS = {
    "schema_version",
    "id",
    "name",
    "version",
    "status",
    "owner",
    "support_tier",
    "engine_compatibility",
    "domains",
    "non_goals",
    "fixtures",
    "deprecation",
    "rules",
}


def pack_roots():
    """Return candidate pack roots in priority order."""
    roots = []

    override = os.environ.get("BEACON_PACKS_DIR")
    if override:
        roots.append(Path(override).expanduser())

    roots.append(Path.cwd() / "packs")
    roots.append(Path(__file__).resolve().parent.parent / "packs")

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(bundle_root) / "packs")

    unique = []
    seen = set()
    for root in roots:
        resolved = root.resolve() if root.exists() else root
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(root)

    return unique


def _pack_files():
    for root in pack_roots():
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            for filename in PACK_FILENAMES:
                pack_file = child / filename
                if pack_file.exists():
                    yield pack_file
                    break


def _load_pack_file(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Pack file must be a YAML mapping: {path}")

    pack_id = data.get("id") or path.parent.name
    data["id"] = pack_id
    data["path"] = str(path)
    data["rules"] = data.get("rules") or []
    return data


def list_packs():
    """List available readiness packs keyed by pack id."""
    packs = {}
    for path in _pack_files():
        pack = _load_pack_file(path)
        packs.setdefault(pack["id"], pack)
    return packs


def get_pack(pack_id):
    packs = list_packs()
    return packs.get(pack_id)


def pack_rule_ids(pack):
    rule_ids = []
    for item in pack.get("rules") or []:
        if isinstance(item, str):
            rule_ids.append(item)
        elif isinstance(item, dict) and item.get("rule_id"):
            rule_ids.append(item["rule_id"])
    return rule_ids


def pack_rules_with_metadata(pack):
    metadata = metadata_registry.list_rules()
    rows = []
    for rule_id in pack_rule_ids(pack):
        rule_metadata = metadata.get(rule_id) or {}
        rows.append(
            {
                "rule_id": rule_id,
                "title": rule_metadata.get("title", ""),
                "category": rule_metadata.get("category", ""),
                "severity_default": rule_metadata.get("severity_default", ""),
                "recommendation": rule_metadata.get("recommendation", ""),
                "metadata_found": bool(rule_metadata),
            }
        )
    return rows


def pack_summary(pack):
    """Return review-friendly coverage and release-gate summary for a pack."""
    rows = pack_rules_with_metadata(pack)
    severity_counts = {}
    category_counts = {}
    domain_counts = {}
    release_gate_count = 0
    advisory_count = 0

    for row in rows:
        severity = row.get("severity_default") or "UNKNOWN"
        category = row.get("category") or "uncategorized"
        rule_id = row.get("rule_id") or ""
        domain = rule_id.split(".", 1)[0] if "." in rule_id else "unknown"

        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        if severity in {"CRITICAL", "ERROR", "HIGH"}:
            release_gate_count += 1
        else:
            advisory_count += 1

    validation = validate_pack(pack)
    return {
        "pack_id": pack.get("id"),
        "schema_version": pack.get("schema_version"),
        "version": pack.get("version"),
        "status": pack.get("status"),
        "owner": pack.get("owner"),
        "support_tier": pack.get("support_tier"),
        "engine_compatible": validation["engine_compatible"],
        "manifest_valid": validation["valid"],
        "manifest_errors": validation["errors"],
        "rule_count": validation["rule_count"],
        "metadata_backed": not validation["missing_metadata"],
        "missing_metadata": validation["missing_metadata"],
        "release_gate_rules": release_gate_count,
        "advisory_rules": advisory_count,
        "severity_counts": dict(sorted(severity_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
    }


def validate_pack(pack, engine_version=None):
    metadata = metadata_registry.list_rules()
    rule_ids = pack_rule_ids(pack)
    missing_fields = sorted(field for field in PACK_REQUIRED_FIELDS if field not in pack)
    errors = []
    if missing_fields:
        errors.append("Missing required manifest fields: " + ", ".join(missing_fields))

    if pack.get("schema_version") != PACK_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PACK_SCHEMA_VERSION}")
    if not semantic_version(pack.get("version")):
        errors.append("version must use semantic versioning (for example 1.2.3)")
    if pack.get("status") not in PACK_STATUSES:
        errors.append("status must be one of: preview, stable, deprecated")
    if pack.get("support_tier") not in PACK_SUPPORT_TIERS:
        errors.append("support_tier must be one of: experimental, supported, critical")
    if not pack.get("owner"):
        errors.append("owner must name an accountable team")
    if not isinstance(pack.get("domains"), list) or not pack.get("domains"):
        errors.append("domains must be a non-empty list")
    if not isinstance(pack.get("non_goals"), list) or not pack.get("non_goals"):
        errors.append("non_goals must be a non-empty list")
    if not rule_ids:
        errors.append("rules must contain at least one rule_id")

    compatibility = pack.get("engine_compatibility") or {}
    minimum = compatibility.get("min_version")
    maximum = compatibility.get("max_version_exclusive")
    if not semantic_version(minimum) or not semantic_version(maximum):
        errors.append(
            "engine_compatibility requires semantic min_version and max_version_exclusive"
        )
    elif version_tuple(minimum) >= version_tuple(maximum):
        errors.append("engine_compatibility min_version must be lower than max_version_exclusive")

    fixtures = pack.get("fixtures")
    if not isinstance(fixtures, list):
        errors.append("fixtures must be a list")
        fixtures = []
    missing_fixtures = sorted(
        fixture_path
        for fixture_path in (
            fixture.get("path") for fixture in fixtures if isinstance(fixture, dict)
        )
        if fixture_path and not fixture_exists(pack, fixture_path)
    )
    if missing_fixtures:
        errors.append("Fixture paths do not exist: " + ", ".join(missing_fixtures))
    if pack.get("status") == "stable" and not fixtures:
        errors.append("stable packs require at least one fixture")

    deprecation = pack.get("deprecation")
    if not isinstance(deprecation, dict):
        errors.append("deprecation must be a mapping")
    elif pack.get("status") == "deprecated" and not deprecation.get("removal_after"):
        errors.append("deprecated packs require deprecation.removal_after")

    engine_version = engine_version or engine_metadata()["version"]
    compatible = engine_is_compatible(compatibility, engine_version)
    if compatible is False:
        errors.append(f"Beacon engine {engine_version} is outside the supported pack range")

    return {
        "pack_id": pack.get("id"),
        "rule_count": len(rule_ids),
        "missing_metadata": sorted(rule_id for rule_id in rule_ids if rule_id not in metadata),
        "missing_fields": missing_fields,
        "missing_fixtures": missing_fixtures,
        "engine_version": engine_version,
        "engine_compatible": compatible,
        "errors": errors,
        "valid": not errors and not any(rule_id not in metadata for rule_id in rule_ids),
    }


def semantic_version(value):
    return version_tuple(value) is not None


def version_tuple(value):
    parts = str(value or "").split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def engine_is_compatible(compatibility, engine_version):
    current = version_tuple(engine_version)
    minimum = version_tuple((compatibility or {}).get("min_version"))
    maximum = version_tuple((compatibility or {}).get("max_version_exclusive"))
    if current is None or minimum is None or maximum is None:
        return None
    return minimum <= current < maximum


def fixture_exists(pack, fixture_path):
    path = Path(fixture_path).expanduser()
    if path.is_absolute():
        return path.exists()
    manifest_path = Path(pack.get("path") or "")
    repository_root = manifest_path.parent.parent.parent if manifest_path else Path.cwd()
    return (repository_root / path).exists()
