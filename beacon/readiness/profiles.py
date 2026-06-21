PROFILE_ALIASES = {
    "production": "prod",
    "prd": "prod",
    "prod": "prod",
    "mission_critical": "mission-critical",
    "missioncritical": "mission-critical",
    "critical": "mission-critical",
    "stage": "staging",
    "stg": "staging",
    "staging": "staging",
    "qa": "test",
    "testing": "test",
    "test": "test",
    "non-prod": "nonprod",
    "nonprod": "nonprod",
    "development": "dev",
    "sandbox": "dev",
    "poc": "dev",
    "dev": "dev",
}


BUILTIN_ENVIRONMENT_PROFILES = {
    "dev": {
        "description": "Developer/sandbox profile. HA-only Kafka topology findings can be informational when intentional.",
        "rule_severities": {
            "kafka.cluster.broker_count.low": "INFO",
            "kafka.topic.replication_factor.low": "INFO",
            "kafka.broker.default_replication_factor.low": "INFO",
            "kafka.broker.offsets_replication_factor.low": "INFO",
            "kafka.broker.transaction_log_replication_factor.low": "INFO",
            "kafka.topic.owner.missing": "LOW",
            "topology.service.owner.missing": "LOW",
            "kafka.consumer_group.offsets.missing": "INFO",
        },
    },
    "test": {
        "description": "Shared test profile. HA-only Kafka topology findings are low risk; data, schema, and security findings remain material.",
        "rule_severities": {
            "kafka.cluster.broker_count.low": "LOW",
            "kafka.topic.replication_factor.low": "LOW",
            "kafka.broker.default_replication_factor.low": "LOW",
            "kafka.broker.offsets_replication_factor.low": "LOW",
            "kafka.broker.transaction_log_replication_factor.low": "LOW",
            "kafka.topic.owner.missing": "LOW",
            "topology.service.owner.missing": "LOW",
            "kafka.consumer_group.offsets.missing": "INFO",
        },
    },
    "nonprod": {
        "description": "Generic non-production profile. Similar to test when the exact tier is unknown.",
        "rule_severities": {
            "kafka.cluster.broker_count.low": "INFO",
            "kafka.topic.replication_factor.low": "INFO",
            "kafka.broker.default_replication_factor.low": "INFO",
            "kafka.broker.offsets_replication_factor.low": "INFO",
            "kafka.broker.transaction_log_replication_factor.low": "INFO",
            "kafka.topic.owner.missing": "LOW",
            "topology.service.owner.missing": "LOW",
            "kafka.consumer_group.offsets.missing": "INFO",
        },
    },
    "staging": {
        "description": "Production-like staging profile. HA findings are release-significant but less severe than production.",
        "rule_severities": {
            "kafka.cluster.broker_count.low": "HIGH",
            "kafka.topic.replication_factor.low": "HIGH",
            "kafka.broker.default_replication_factor.low": "HIGH",
            "kafka.broker.offsets_replication_factor.low": "HIGH",
            "kafka.broker.transaction_log_replication_factor.low": "HIGH",
            "kafka.topic.owner.missing": "LOW",
            "topology.service.owner.missing": "LOW",
            "kafka.consumer_group.offsets.missing": "INFO",
        },
    },
    "prod": {
        "description": "Production profile. HA, durability, ownership, security, and compatibility findings remain release-significant.",
        "rule_severities": {},
    },
    "mission-critical": {
        "description": "Strict production profile for high-criticality systems.",
        "rule_severities": {
            "kafka.topic.partitions.low": "MEDIUM",
            "kafka.topic.owner.missing": "MEDIUM",
            "topology.service.owner.missing": "MEDIUM",
            "schema_registry.compatibility.global_unsafe": "CRITICAL",
        },
    },
}


def normalize_environment_profile(environment):
    if not isinstance(environment, str) or not environment.strip():
        return environment

    key = environment.strip().lower().replace(" ", "-")
    return PROFILE_ALIASES.get(key, key)


def profile_for(environment):
    return BUILTIN_ENVIRONMENT_PROFILES.get(normalize_environment_profile(environment))


def profile_rule_severity(environment, rule_id):
    profile = profile_for(environment)
    if not profile:
        return None
    return profile.get("rule_severities", {}).get(rule_id)


def profile_adjustment_reason(environment):
    profile = profile_for(environment) or {}
    return profile.get("description") or f"Adjusted by the {environment} readiness profile."
