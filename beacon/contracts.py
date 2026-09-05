"""Stable metadata and validation helpers for Beacon's public JSON contracts."""

from datetime import datetime, timezone

from beacon import __version__

REPORT_SCHEMA_VERSION = "1.0.0"
RELEASE_EVIDENCE_SCHEMA_VERSION = "1.0.0"
SUPPORTED_RELEASE_EVIDENCE_SCHEMA_MAJORS = {1}


class ContractError(ValueError):
    """Raised when a public Beacon artifact violates its declared contract."""


def utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def engine_metadata():
    return {"name": "beacon-readiness", "version": __version__}


def contract_metadata(schema_version):
    return {
        "schema_version": schema_version,
        "generated_at": utc_timestamp(),
        "engine": engine_metadata(),
    }


def validate_release_evidence(payload, allow_legacy=False):
    """Validate the stable release-evidence envelope.

    Legacy, unversioned evidence can still be compared when ``allow_legacy`` is
    true, which keeps existing team baselines usable during the v1 migration.
    """
    if not isinstance(payload, dict):
        raise ContractError("Release evidence must be a JSON object.")

    schema_version = payload.get("schema_version")
    if schema_version is None:
        if allow_legacy:
            return payload
        raise ContractError("Release evidence is missing schema_version.")

    try:
        major = int(str(schema_version).split(".", 1)[0])
    except (TypeError, ValueError) as error:
        raise ContractError(
            "Release evidence schema_version must use semantic versioning."
        ) from error

    if major not in SUPPORTED_RELEASE_EVIDENCE_SCHEMA_MAJORS:
        supported = ", ".join(
            str(item) for item in sorted(SUPPORTED_RELEASE_EVIDENCE_SCHEMA_MAJORS)
        )
        raise ContractError(
            f"Unsupported release-evidence schema major {major}; supported major(s): {supported}."
        )

    required = {
        "generated_at": str,
        "engine": dict,
        "decision": str,
        "score": (int, float),
        "counts": dict,
        "blocking_risks": list,
        "major_risks": list,
        "production_blockers": dict,
    }
    for field, expected_type in required.items():
        if field not in payload:
            raise ContractError(f"Release evidence is missing required field '{field}'.")
        if not isinstance(payload[field], expected_type):
            raise ContractError(f"Release evidence field '{field}' has an invalid type.")
    return payload
