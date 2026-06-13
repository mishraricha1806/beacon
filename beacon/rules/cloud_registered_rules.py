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

    if resource_type != "aws_db_instance" or config.get("publicly_accessible") is not True:
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


def autoscaling_capacity_insufficient(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_autoscaling_group":
        return None

    desired = config.get("desired_capacity")
    maximum = config.get("max_size")
    minimum = config.get("min_size")

    if desired is None or maximum is None:
        return None

    if maximum > desired and (minimum is None or maximum >= minimum):
        return None

    return build_cloud_finding(
        resource,
        "cloud.compute.autoscaling.capacity.insufficient",
        "scalability",
        "HIGH",
        f"Autoscaling group '{resource.name}' has no scale-out headroom",
        "An autoscaling group with desired capacity already at max size cannot absorb demand spikes or node replacement without manual intervention.",
        "Increase max_size above desired_capacity and validate the min/max range against production capacity policy.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "desired_capacity": desired,
            "max_size": maximum,
            "min_size": minimum,
        },
        ["cloud", "compute", "autoscaling"],
    )


def quota_headroom_insufficient(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "cloud_quota_profile":
        return None

    quota_limit = config.get("quota_limit")
    required_capacity = config.get("required_capacity")
    reserved_buffer = config.get("reserved_buffer", 0)

    if quota_limit is None or required_capacity is None:
        return None

    if required_capacity + reserved_buffer <= quota_limit:
        return None

    return build_cloud_finding(
        resource,
        "cloud.quota.headroom.insufficient",
        "scalability",
        "CRITICAL",
        f"Cloud quota profile '{resource.name}' lacks deployment headroom",
        "Requested capacity plus required safety buffer exceeds available quota and can block deployment or autoscaling.",
        "Increase approved quota, reduce requested capacity, or adjust the reserved buffer with explicit review before production rollout.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "quota_limit": quota_limit,
            "required_capacity": required_capacity,
            "reserved_buffer": reserved_buffer,
        },
        ["cloud", "quota", "capacity"],
    )


def rds_multi_az_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_db_instance" or config.get("multi_az") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.multi_az.disabled",
        "resiliency",
        "HIGH",
        f"RDS instance '{resource.name}' does not enable Multi-AZ",
        "Single-AZ databases have weaker failover posture and increase outage risk during AZ disruption or maintenance.",
        "Enable Multi-AZ or document an approved environment-specific exception for non-production tiers.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "multi_az": config.get("multi_az"),
        },
        ["cloud", "database", "ha"],
    )


def rds_private_subnet_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_db_instance":
        return None

    if config.get("publicly_accessible") is True:
        return None

    subnet_group = config.get("db_subnet_group_name")
    if subnet_group:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.private_subnet.missing",
        "operational_safety",
        "HIGH",
        f"RDS instance '{resource.name}' has no explicit private subnet placement",
        "Databases without a defined DB subnet group can drift into weaker network placement and create uncertain private access posture.",
        "Attach RDS instances to approved private DB subnet groups and validate route isolation before production rollout.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "db_subnet_group_name": subnet_group,
            "publicly_accessible": config.get("publicly_accessible"),
        },
        ["cloud", "database", "network"],
    )


def vpc_endpoint_private_dns_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_vpc_endpoint":
        return None

    if config.get("private_dns_enabled") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.network.vpc_endpoint.private_dns.disabled",
        "operational_safety",
        "MEDIUM",
        f"VPC endpoint '{resource.name}' does not enable private DNS",
        "Private endpoints without private DNS are easier to bypass and can lead clients back to public service endpoints.",
        "Enable private_dns_enabled for interface endpoints that should enforce private access paths.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "private_dns_enabled": config.get("private_dns_enabled"),
        },
        ["cloud", "network", "private-endpoint"],
    )


def region_high_availability_missing(resource, context):
    resources = [
        item
        for item in context.get("resources", [])
        if item.type == "cloud_resource"
        and item.attributes.get("provider_resource_type") != "cloud_quota_profile"
    ]

    if not resources:
        return None

    anchor = min(resources, key=lambda item: (item.source, item.name))
    if resource.name != anchor.name or resource.source != anchor.source:
        return None

    regions = {
        item.attributes.get("config", {}).get("region")
        for item in resources
        if item.attributes.get("config", {}).get("region")
    }

    environments = {
        str(
            item.attributes.get("config", {}).get("environment")
            or (item.attributes.get("config", {}).get("tags") or {}).get("environment")
            or ""
        ).lower()
        for item in resources
    }

    prod_like = any(value in {"prod", "production"} for value in environments)
    if not prod_like or len(regions) != 1:
        return None

    return build_cloud_finding(
        resource,
        "cloud.region.high_availability.missing",
        "resiliency",
        "HIGH",
        "Cloud deployment spans only one region",
        "Production resources concentrated in one region have weaker disaster tolerance and limited regional failover options.",
        "Distribute critical production resources across multiple approved regions or document an explicit single-region exception.",
        {
            "regions": sorted(regions),
            "environment_markers": sorted(value for value in environments if value),
            "resource_count": len(resources),
        },
        ["cloud", "resiliency", "multi-region"],
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
register(
    "cloud.compute.autoscaling.capacity.insufficient",
    "scalability",
    "HIGH",
    "Autoscaling capacity headroom insufficient",
    "Detects autoscaling groups without scale-out headroom.",
    autoscaling_capacity_insufficient,
    ["cloud", "compute", "autoscaling"],
)
register(
    "cloud.quota.headroom.insufficient",
    "scalability",
    "CRITICAL",
    "Cloud quota headroom insufficient",
    "Detects declared cloud quota profiles that cannot satisfy requested capacity plus buffer.",
    quota_headroom_insufficient,
    ["cloud", "quota", "capacity"],
)
register(
    "cloud.database.rds.multi_az.disabled",
    "resiliency",
    "HIGH",
    "RDS Multi-AZ disabled",
    "Detects RDS instances that do not enable Multi-AZ.",
    rds_multi_az_disabled,
    ["cloud", "database", "ha"],
)
register(
    "cloud.database.rds.private_subnet.missing",
    "operational_safety",
    "HIGH",
    "RDS private subnet placement missing",
    "Detects RDS instances without explicit DB subnet group placement.",
    rds_private_subnet_missing,
    ["cloud", "database", "network"],
)
register(
    "cloud.network.vpc_endpoint.private_dns.disabled",
    "operational_safety",
    "MEDIUM",
    "VPC endpoint private DNS disabled",
    "Detects interface VPC endpoints that do not enable private DNS.",
    vpc_endpoint_private_dns_disabled,
    ["cloud", "network", "private-endpoint"],
)
register(
    "cloud.region.high_availability.missing",
    "resiliency",
    "HIGH",
    "Single-region production deployment",
    "Detects production cloud resource sets concentrated in one region.",
    region_high_availability_missing,
    ["cloud", "resiliency", "multi-region"],
)
