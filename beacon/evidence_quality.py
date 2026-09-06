"""Attach transparent evidence-quality metadata to Beacon findings."""

from datetime import datetime, timezone


def annotate_evidence_quality(findings, now=None, default_max_age_hours=24):
    """Ensure every finding explains its confidence and evidence freshness.

    Existing domain-specific assessments take precedence. Unknown freshness is
    explicit rather than being interpreted as current.
    """
    now = now or datetime.now(timezone.utc)
    for item in findings or []:
        evidence = item.setdefault("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {"value": evidence}
            item["evidence"] = evidence
        if isinstance(evidence.get("assessment"), dict):
            continue

        observed_at = _first_timestamp(evidence)
        age_hours = _age_hours(observed_at, now)
        if age_hours is None:
            freshness = "UNKNOWN"
        elif age_hours <= default_max_age_hours:
            freshness = "CURRENT"
        else:
            freshness = "STALE"

        evidence["assessment"] = {
            "confidence": "MEDIUM" if evidence else "LOW",
            "freshness": freshness,
            "evidence_bound": True,
        }
    return findings


def _first_timestamp(evidence):
    for key in ("captured_at", "observed_at", "generated_at", "timestamp"):
        if evidence.get(key):
            return evidence[key]
    return None


def _age_hours(value, now):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 3600)
    except (TypeError, ValueError):
        return None
