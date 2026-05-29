from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_cloud_finding(
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
        domain="cloud",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def security_group_open_ingress(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_security_group":
        return None

    offending_rules = []

    for rule in config.get("ingress", []) or []:
        cidrs = normalize_cidrs(rule.get("cidr_blocks") or [])
        ipv6_cidrs = normalize_cidrs(rule.get("ipv6_cidr_blocks") or [])
        from_port = rule.get("from_port")
        to_port = rule.get("to_port")

        if "0.0.0.0/0" in cidrs or "::/0" in ipv6_cidrs:
            offending_rules.append(
                {
                    "from_port": from_port,
                    "to_port": to_port,
                    "cidr_blocks": cidrs,
                    "ipv6_cidr_blocks": ipv6_cidrs,
                }
            )

    if not offending_rules:
        return None

    return build_cloud_finding(
        resource,
        "cloud.network.security_group.open_ingress",
        "operational_safety",
        "HIGH",
        f"Security group '{resource.name}' allows public ingress",
        "Public ingress can expose services directly to the internet and increase attack surface.",
        "Restrict ingress CIDRs to trusted networks or front services with approved load balancers and WAF controls.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "offending_rules": offending_rules,
        },
        ["cloud", "network", "security-group"],
    )


def normalize_cidrs(values):
    return [value.strip('"') if isinstance(value, str) else value for value in values]


def rds_public_access(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if (
        resource_type != "aws_db_instance"
        or config.get("publicly_accessible") is not True
    ):
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.publicly_accessible",
        "operational_safety",
        "CRITICAL",
        f"RDS instance '{resource.name}' is publicly accessible",
        "Public database exposure can lead to data compromise and broad operational blast radius.",
        "Disable public accessibility and place databases in private subnets with least-privilege network access.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "publicly_accessible": True,
        },
        ["cloud", "database", "rds"],
    )


def rds_backup_retention_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_db_instance":
        return None

    retention = config.get("backup_retention_period")

    if retention is not None and retention > 0:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.backup_retention_missing",
        "recovery_readiness",
        "HIGH",
        f"RDS instance '{resource.name}' has no backup retention",
        "Missing database backups reduce recovery ability after corruption, deletion, or operational mistakes.",
        "Set backup_retention_period to a production-appropriate value and validate restore procedures.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "backup_retention_period": retention,
        },
        ["cloud", "database", "backup"],
    )


def ec2_detailed_monitoring_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_instance" or config.get("monitoring") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.compute.ec2.detailed_monitoring.disabled",
        "operational_safety",
        "LOW",
        f"EC2 instance '{resource.name}' does not enable detailed monitoring",
        "Weak monitoring granularity can delay capacity and degradation detection.",
        "Enable detailed monitoring for critical production instances or ensure equivalent telemetry exists.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "monitoring": config.get("monitoring"),
        },
        ["cloud", "compute", "monitoring"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="cloud",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["cloud_resource"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "cloud.network.security_group.open_ingress",
    "operational_safety",
    "HIGH",
    "Cloud security group public ingress",
    "Detects security groups with public ingress CIDRs.",
    security_group_open_ingress,
    ["cloud", "network", "security-group"],
)

register(
    "cloud.database.rds.publicly_accessible",
    "operational_safety",
    "CRITICAL",
    "RDS publicly accessible",
    "Detects publicly accessible RDS instances.",
    rds_public_access,
    ["cloud", "database", "rds"],
)

register(
    "cloud.database.rds.backup_retention_missing",
    "recovery_readiness",
    "HIGH",
    "RDS backup retention missing",
    "Detects RDS instances without backup retention.",
    rds_backup_retention_missing,
    ["cloud", "database", "backup"],
)

register(
    "cloud.compute.ec2.detailed_monitoring.disabled",
    "operational_safety",
    "LOW",
    "EC2 detailed monitoring disabled",
    "Detects EC2 instances without detailed monitoring.",
    ec2_detailed_monitoring_disabled,
    ["cloud", "compute", "monitoring"],
)
