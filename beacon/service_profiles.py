"""Deterministic service-tier and ownership governance profiles."""

TIER_POLICIES = {
    "tier-0": {
        "rank": 0,
        "recommended_fail_on": "medium",
        "approval": "service owner and SRE/platform approver",
        "required_controls": [
            "named service owner and on-call route",
            "documented SLO and error-budget policy",
            "tested rollback and recovery procedure",
            "current runbook for critical business flows",
        ],
    },
    "tier-1": {
        "rank": 1,
        "recommended_fail_on": "high",
        "approval": "service owner",
        "required_controls": [
            "named service owner and escalation route",
            "documented availability objective",
            "tested rollback procedure",
        ],
    },
    "tier-2": {
        "rank": 2,
        "recommended_fail_on": "critical",
        "approval": "service owner or delegated reviewer",
        "required_controls": [
            "named service owner",
            "documented rollback procedure",
        ],
    },
    "tier-3": {
        "rank": 3,
        "recommended_fail_on": "critical",
        "approval": "team reviewer",
        "required_controls": ["named owning team"],
    },
}

CRITICALITY_TIERS = {
    "mission-critical": "tier-0",
    "critical": "tier-0",
    "highest": "tier-0",
    "high": "tier-1",
    "medium": "tier-2",
    "normal": "tier-2",
    "low": "tier-3",
    "development": "tier-3",
}


def normalize_tier(value, criticality=None):
    text = ("" if value is None else str(value)).strip().lower().replace("_", "-")
    aliases = {
        "0": "tier-0",
        "tier0": "tier-0",
        "tier-0": "tier-0",
        "1": "tier-1",
        "tier1": "tier-1",
        "tier-1": "tier-1",
        "2": "tier-2",
        "tier2": "tier-2",
        "tier-2": "tier-2",
        "3": "tier-3",
        "tier3": "tier-3",
        "tier-3": "tier-3",
    }
    if text in aliases:
        return aliases[text]
    return CRITICALITY_TIERS.get(str(criticality or "medium").strip().lower(), "tier-2")


def normalize_service_profiles(services, environment_owner=None, environment_criticality=None):
    profiles = []
    for item in services or []:
        raw = {"name": item} if isinstance(item, str) else dict(item or {})
        name = raw.get("name") or raw.get("service") or raw.get("id")
        if not name:
            continue
        criticality = raw.get("criticality") or environment_criticality or "medium"
        tier = normalize_tier(raw.get("tier"), criticality)
        policy = TIER_POLICIES[tier]
        profiles.append(
            {
                "name": str(name),
                "owner": raw.get("owner") or environment_owner,
                "on_call": raw.get("on_call") or raw.get("on-call"),
                "tier": tier,
                "criticality": criticality,
                "business_flows": list(raw.get("business_flows") or []),
                "repository": raw.get("repository"),
                "recommended_fail_on": policy["recommended_fail_on"],
                "required_approval": policy["approval"],
                "required_controls": list(policy["required_controls"]),
            }
        )
    return sorted(profiles, key=lambda item: (TIER_POLICIES[item["tier"]]["rank"], item["name"]))


def build_service_governance(
    services,
    environment_owner=None,
    environment_criticality=None,
):
    profiles = normalize_service_profiles(
        services,
        environment_owner=environment_owner,
        environment_criticality=environment_criticality,
    )
    missing_owners = [item["name"] for item in profiles if not item.get("owner")]
    missing_on_call = [
        item["name"]
        for item in profiles
        if item["tier"] in {"tier-0", "tier-1"} and not item.get("on_call")
    ]
    strict_missing_owners = [
        item["name"]
        for item in profiles
        if item["tier"] in {"tier-0", "tier-1"} and not item.get("owner")
    ]
    strictest_tier = (
        profiles[0]["tier"]
        if profiles
        else normalize_tier(None, environment_criticality)
    )
    tier_counts = {tier: 0 for tier in TIER_POLICIES}
    for profile in profiles:
        tier_counts[profile["tier"]] += 1

    if strict_missing_owners:
        status = "BLOCKED"
        reason = "One or more tier-0/tier-1 services have no accountable owner."
    elif not profiles:
        status = "NEEDS_REVIEW"
        reason = "No service profiles were provided."
    elif missing_owners or missing_on_call:
        status = "NEEDS_REVIEW"
        reason = "Service ownership or escalation metadata is incomplete."
    else:
        status = "PASS"
        reason = "Service tiers and accountable ownership are defined."

    owned_count = len(profiles) - len(missing_owners)
    return {
        "status": status,
        "reason": reason,
        "service_count": len(profiles),
        "owned_service_count": owned_count,
        "ownership_coverage_percent": round(100 * owned_count / len(profiles)) if profiles else 0,
        "strictest_tier": strictest_tier,
        "recommended_fail_on": TIER_POLICIES[strictest_tier]["recommended_fail_on"],
        "required_approval": TIER_POLICIES[strictest_tier]["approval"],
        "tier_counts": tier_counts,
        "missing_owners": missing_owners,
        "missing_on_call": missing_on_call,
        "profiles": profiles,
    }
