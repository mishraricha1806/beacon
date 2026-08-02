"""Inspectable readiness pack catalog.

Packs are not a second rule engine. They are a public, reviewable layer that
groups Beacon's deterministic rule IDs into product-ready readiness domains.
"""

import os
import sys
from pathlib import Path

import yaml

from beacon.engine import metadata_registry

PACK_FILENAMES = ("pack.yaml", "pack.yml")


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
        packs[pack["id"]] = pack
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
        "rule_count": validation["rule_count"],
        "metadata_backed": not validation["missing_metadata"],
        "missing_metadata": validation["missing_metadata"],
        "release_gate_rules": release_gate_count,
        "advisory_rules": advisory_count,
        "severity_counts": dict(sorted(severity_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
    }


def validate_pack(pack):
    metadata = metadata_registry.list_rules()
    rule_ids = pack_rule_ids(pack)
    return {
        "pack_id": pack.get("id"),
        "rule_count": len(rule_ids),
        "missing_metadata": sorted(rule_id for rule_id in rule_ids if rule_id not in metadata),
    }
