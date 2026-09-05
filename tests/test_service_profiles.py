from beacon.service_profiles import build_service_governance, normalize_service_profiles


def test_service_profiles_normalize_tiers_and_inherit_environment_owner():
    profiles = normalize_service_profiles(
        [
            {"name": "payments", "tier": 0, "owner": "team-payments", "on_call": "pd-pay"},
            {"name": "orders", "criticality": "high"},
            "reporting",
        ],
        environment_owner="platform-team",
        environment_criticality="medium",
    )

    assert [item["name"] for item in profiles] == ["payments", "orders", "reporting"]
    assert profiles[0]["tier"] == "tier-0"
    assert profiles[0]["recommended_fail_on"] == "medium"
    assert profiles[1]["tier"] == "tier-1"
    assert profiles[1]["owner"] == "platform-team"
    assert profiles[2]["tier"] == "tier-2"


def test_high_tier_missing_owner_blocks_service_governance():
    governance = build_service_governance(
        [{"name": "checkout", "tier": "tier-0"}],
        environment_criticality="critical",
    )

    assert governance["status"] == "BLOCKED"
    assert governance["strictest_tier"] == "tier-0"
    assert governance["recommended_fail_on"] == "medium"
    assert governance["missing_owners"] == ["checkout"]
    assert governance["ownership_coverage_percent"] == 0


def test_complete_tier_one_profile_passes_governance():
    governance = build_service_governance(
        [
            {
                "name": "checkout",
                "tier": "tier-1",
                "owner": "team-checkout",
                "on_call": "pagerduty-checkout",
            }
        ]
    )

    assert governance["status"] == "PASS"
    assert governance["ownership_coverage_percent"] == 100
    assert governance["required_approval"] == "service owner"
