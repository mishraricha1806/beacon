from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_storage_finding(
    resource,
    rule_id,
    category,
    severity,
    title,
    impact,
    recommendation,
    evidence,
    tags=None,
):
    return Finding(
        rule_id=rule_id,
        domain="storage",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def capacity_high(resource, context):
    used = resource.attributes.get("used_percent")

    if used is None or used < 85:
        return None

    severity = "CRITICAL" if used >= 95 else "HIGH"

    return build_storage_finding(
        resource,
        "storage.runtime.capacity.high",
        "storage_sustainability",
        severity,
        f"Storage resource '{resource.name}' usage is high",
        "Storage saturation can cause write failures, retention pressure, and recovery instability.",
        "Create capacity headroom and review growth drivers, retention policy, and cleanup safety.",
        {
            "resource": resource.name,
            "resource_type": resource.attributes.get("resource_type"),
            "used_percent": used,
        },
        ["storage", "capacity"],
    )


def growth_high(resource, context):
    growth = resource.attributes.get("growth_percent_7d")

    if growth is None or growth < 20:
        return None

    return build_storage_finding(
        resource,
        "storage.runtime.growth_rate.high",
        "storage_sustainability",
        "HIGH",
        f"Storage resource '{resource.name}' is growing quickly",
        "Fast storage growth can exhaust capacity before normal planning cycles catch up.",
        "Investigate workload changes, retention policy, payload size, and cleanup behavior.",
        {
            "resource": resource.name,
            "resource_type": resource.attributes.get("resource_type"),
            "growth_percent_7d": growth,
        },
        ["storage", "growth"],
    )


def iops_saturation(resource, context):
    saturation = resource.attributes.get("iops_saturation_percent")

    if saturation is None or saturation < 85:
        return None

    return build_storage_finding(
        resource,
        "storage.runtime.iops_saturation.high",
        "runtime_stability",
        "HIGH",
        f"Storage resource '{resource.name}' has high I/O saturation",
        "I/O saturation can increase application latency and slow recovery operations.",
        "Review disk class, hot partitions, query patterns, compaction, and workload distribution.",
        {
            "resource": resource.name,
            "resource_type": resource.attributes.get("resource_type"),
            "iops_saturation_percent": saturation,
        },
        ["storage", "iops"],
    )


def backup_stale(resource, context):
    backup_age = resource.attributes.get("backup_age_hours")

    if backup_age is None or backup_age <= 24:
        return None

    severity = "CRITICAL" if backup_age > 72 else "HIGH"

    return build_storage_finding(
        resource,
        "storage.runtime.backup_stale",
        "recovery_readiness",
        severity,
        f"Storage resource '{resource.name}' backup is stale",
        "Stale backups increase data-loss exposure during recovery.",
        "Verify backup jobs, snapshot policy, restore testing, and alerting for backup freshness.",
        {
            "resource": resource.name,
            "resource_type": resource.attributes.get("resource_type"),
            "backup_age_hours": backup_age,
        },
        ["storage", "backup", "recovery"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="storage",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["storage_runtime_resource"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "storage.runtime.capacity.high",
    "storage_sustainability",
    "HIGH",
    "Storage capacity high",
    "Detects storage resources with high utilization.",
    capacity_high,
    ["storage", "capacity"],
)
register(
    "storage.runtime.growth_rate.high",
    "storage_sustainability",
    "HIGH",
    "Storage growth rate high",
    "Detects fast-growing storage resources.",
    growth_high,
    ["storage", "growth"],
)
register(
    "storage.runtime.iops_saturation.high",
    "runtime_stability",
    "HIGH",
    "Storage I/O saturation high",
    "Detects high storage I/O saturation.",
    iops_saturation,
    ["storage", "iops"],
)
register(
    "storage.runtime.backup_stale",
    "recovery_readiness",
    "HIGH",
    "Storage backup stale",
    "Detects stale storage backups.",
    backup_stale,
    ["storage", "backup"],
)
