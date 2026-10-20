import re
from pathlib import Path

import pytest

from beacon import __version__
from beacon.contracts import ContractError, validate_release_evidence


def release_evidence(schema_version="1.0.0"):
    return {
        "schema_version": schema_version,
        "generated_at": "2026-08-29T00:00:00+00:00",
        "engine": {"name": "beacon-readiness", "version": "0.1.10"},
        "decision": "READY",
        "score": 100,
        "counts": {},
        "blocking_risks": [],
        "major_risks": [],
        "production_blockers": {},
    }


def test_release_evidence_v1_contract_is_accepted():
    payload = release_evidence()

    assert validate_release_evidence(payload) is payload


def test_unknown_release_evidence_major_is_rejected():
    with pytest.raises(ContractError, match="Unsupported release-evidence schema major 2"):
        validate_release_evidence(release_evidence("2.0.0"))


def test_unversioned_release_evidence_requires_explicit_legacy_mode():
    payload = {"decision": "READY"}

    with pytest.raises(ContractError, match="missing schema_version"):
        validate_release_evidence(payload)

    assert validate_release_evidence(payload, allow_legacy=True) is payload


def test_runtime_version_matches_package_metadata():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

    assert match
    assert __version__ == match.group(1)
