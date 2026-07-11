from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry

AZURE_DATABASE_RESOURCE_TYPES = {
    "azurerm_mssql_server",
    "azurerm_mysql_flexible_server",
    "azurerm_postgresql_flexible_server",
}

AZURE_PRIVATE_ENDPOINT_TARGET_TYPES = AZURE_DATABASE_RESOURCE_TYPES | {
    "azurerm_key_vault",
}

AZURE_VM_SCALE_SET_RESOURCE_TYPES = {
    "azurerm_linux_virtual_machine_scale_set",
    "azurerm_windows_virtual_machine_scale_set",
}


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


def terraform_unknown_after_apply_correlation_gap(resource, context):
    if resource.attributes.get("provider_resource_type") != "terraform_unknown_after_apply":
        return None

    sensitive_paths = resource.attributes.get("correlation_sensitive_unknown_paths") or []

    if not sensitive_paths:
        return None

    return build_cloud_finding(
        resource,
        "terraform.plan.unknown_after_apply.correlation_gap",
        "operational_safety",
        "MEDIUM",
        f"Terraform plan for '{resource.name}' has unknown values needed for correlation",
        (
            "Some dependency identifiers are unknown until apply, so Beacon cannot "
            "strongly correlate this planned resource with live Kubernetes, Kafka, "
            "cloud, or topology evidence yet."
        ),
        (
            "Use stable correlation keys such as service labels, tags, topic names, "
            "Backstage refs, or rerun Beacon after apply with Terraform state and "
            "live snapshots."
        ),
        {
            "resource": resource.name,
            "source_resource_type": resource.attributes.get("source_resource_type"),
            "source_resource_name": resource.attributes.get("source_resource_name"),
            "unknown_paths": resource.attributes.get("unknown_paths") or [],
            "correlation_sensitive_unknown_paths": sensitive_paths,
            "correlation_confidence": "LOW",
            "readiness_model": "intent_based_until_apply",
            "recommended_follow_up": "post_apply_state_or_live_snapshot_verification",
        },
        ["terraform", "plan", "unknown-after-apply", "correlation"],
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


def rds_deletion_protection_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_db_instance" or config.get("deletion_protection") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.deletion_protection.disabled",
        "recovery_readiness",
        "HIGH",
        f"RDS instance '{resource.name}' does not enable deletion protection",
        "Without deletion protection, accidental Terraform or console deletion can remove a production database more easily.",
        "Enable deletion_protection for production databases and require an explicit break-glass workflow for deletion.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "deletion_protection": config.get("deletion_protection"),
        },
        ["cloud", "database", "rds", "recovery"],
    )


def rds_storage_encryption_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_db_instance" or config.get("storage_encrypted") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.rds.storage_encryption.disabled",
        "operational_safety",
        "HIGH",
        f"RDS instance '{resource.name}' does not enable storage encryption",
        "Unencrypted database storage can violate production security requirements and increase exposure during snapshot, backup, or disk compromise scenarios.",
        "Enable storage_encrypted and use an approved KMS key for production databases.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "storage_encrypted": config.get("storage_encrypted"),
            "kms_key_id": config.get("kms_key_id"),
        },
        ["cloud", "database", "rds", "encryption"],
    )


def azure_database_public_access_enabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_DATABASE_RESOURCE_TYPES:
        return None

    public_network_access = config.get("public_network_access_enabled")
    if str(public_network_access).lower() in {"false", "disabled"}:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.azure.public_network_access.enabled",
        "operational_safety",
        "CRITICAL",
        f"Azure managed database '{resource.name}' allows public network access",
        "Public database network access increases data exposure and operational blast radius.",
        "Disable public network access and require private endpoint or approved private connectivity before production.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "public_network_access_enabled": public_network_access,
        },
        ["cloud", "database", "azure", "network"],
    )


def azure_database_backup_retention_weak(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_DATABASE_RESOURCE_TYPES:
        return None

    retention = config.get("backup_retention_days")
    if isinstance(retention, str) and retention.isdigit():
        retention = int(retention)

    if isinstance(retention, (int, float)) and retention >= 7:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.azure.backup_retention.weak",
        "recovery_readiness",
        "HIGH",
        f"Azure managed database '{resource.name}' has weak backup retention",
        "Short or missing backup retention weakens recovery after corruption, deletion, or operational mistakes.",
        "Set backup retention to a production-approved duration and test restore procedures.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "backup_retention_days": retention,
        },
        ["cloud", "database", "azure", "backup"],
    )


def azure_database_ha_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_DATABASE_RESOURCE_TYPES:
        return None

    high_availability = config.get("high_availability")
    zone_redundant = config.get("zone_redundant")

    ha_enabled = False
    if isinstance(high_availability, list):
        ha_enabled = any(
            item.get("mode") not in {None, "Disabled"}
            for item in high_availability
            if isinstance(item, dict)
        )
    elif isinstance(high_availability, dict):
        ha_enabled = high_availability.get("mode") not in {None, "Disabled"}

    if ha_enabled or zone_redundant is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.azure.ha.disabled",
        "resiliency",
        "HIGH",
        f"Azure managed database '{resource.name}' does not enable HA",
        "Single-zone managed databases have weaker failover posture during zone failure or maintenance.",
        "Enable zone-redundant or high-availability mode for production databases, or document an approved exception.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "high_availability": high_availability,
            "zone_redundant": zone_redundant,
        },
        ["cloud", "database", "azure", "ha"],
    )


def azure_database_deletion_protection_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_DATABASE_RESOURCE_TYPES:
        return None

    deletion_protection = first_present(
        config,
        "deletion_protection_enabled",
        "deletion_protection",
        "prevent_destroy",
    )
    if deletion_protection is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.azure.deletion_protection.missing",
        "recovery_readiness",
        "HIGH",
        f"Azure managed database '{resource.name}' has no deletion protection evidence",
        "Without deletion protection or an equivalent break-glass workflow, accidental deletion can remove production data services more easily.",
        "Enable deletion protection where supported, or require a Terraform lifecycle/prevent-destroy and explicit break-glass deletion approval.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "deletion_protection": deletion_protection,
        },
        ["cloud", "database", "azure", "recovery"],
    )


def azure_database_customer_managed_key_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_DATABASE_RESOURCE_TYPES:
        return None

    cmk = first_present(
        config,
        "customer_managed_key_id",
        "key_vault_key_id",
        "data_encryption_key_vault_key_id",
    )
    customer_managed_key = first_block(config.get("customer_managed_key"))
    if cmk or customer_managed_key:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.azure.customer_managed_key.missing",
        "operational_safety",
        "MEDIUM",
        f"Azure managed database '{resource.name}' has no customer-managed key evidence",
        "Production databases without customer-managed key evidence may not satisfy stricter encryption ownership or compliance requirements.",
        "Use a customer-managed key where required by policy, or document that provider-managed encryption is approved for this environment.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "customer_managed_key": customer_managed_key or cmk,
        },
        ["cloud", "database", "azure", "encryption"],
    )


def gcp_sql_public_access_enabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    ip_config = cloud_sql_ip_configuration(config)
    authorized_networks = ip_config.get("authorized_networks") or []
    public_ipv4 = ip_config.get("ipv4_enabled")

    if public_ipv4 is not True and not authorized_networks:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.gcp.public_ip.enabled",
        "operational_safety",
        "CRITICAL",
        f"GCP Cloud SQL instance '{resource.name}' exposes public network access",
        "Public Cloud SQL access increases data exposure and operational blast radius.",
        "Disable public IPv4 or restrict authorized networks behind approved private connectivity.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "ipv4_enabled": public_ipv4,
            "authorized_networks": authorized_networks,
        },
        ["cloud", "database", "gcp", "network"],
    )


def gcp_sql_backup_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    backup_config = cloud_sql_backup_configuration(config)
    if backup_config.get("enabled") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.gcp.backup.disabled",
        "recovery_readiness",
        "HIGH",
        f"GCP Cloud SQL instance '{resource.name}' does not enable backups",
        "Missing database backups reduce recovery ability after corruption, deletion, or operational mistakes.",
        "Enable backup_configuration.enabled and validate restore procedures for production databases.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "backup_configuration": backup_config,
        },
        ["cloud", "database", "gcp", "backup"],
    )


def gcp_sql_deletion_protection_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    if config.get("deletion_protection") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.gcp.deletion_protection.disabled",
        "recovery_readiness",
        "HIGH",
        f"GCP Cloud SQL instance '{resource.name}' does not enable deletion protection",
        "Without deletion protection, accidental Terraform or console deletion can remove a production database more easily.",
        "Enable deletion_protection for production databases and require explicit break-glass deletion approval.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "deletion_protection": config.get("deletion_protection"),
        },
        ["cloud", "database", "gcp", "recovery"],
    )


def gcp_sql_ha_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    settings = cloud_sql_settings(config)
    if settings.get("availability_type") == "REGIONAL":
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.gcp.ha.disabled",
        "resiliency",
        "HIGH",
        f"GCP Cloud SQL instance '{resource.name}' does not enable regional HA",
        "Zonal Cloud SQL instances have weaker failover posture during zone failure or maintenance.",
        "Set availability_type to REGIONAL for production databases or document an approved exception.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "availability_type": settings.get("availability_type"),
        },
        ["cloud", "database", "gcp", "ha"],
    )


def gcp_sql_customer_managed_encryption_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    encryption_key = first_present(
        config,
        "encryption_key_name",
        "disk_encryption_configuration",
        "kms_key_name",
    )
    settings = cloud_sql_settings(config)
    if encryption_key or settings.get("encryption_key_name"):
        return None

    return build_cloud_finding(
        resource,
        "cloud.database.gcp.cmek.missing",
        "operational_safety",
        "MEDIUM",
        f"GCP Cloud SQL instance '{resource.name}' has no customer-managed encryption key evidence",
        "Production databases without CMEK evidence may not satisfy encryption ownership, key-rotation, or compliance requirements.",
        "Configure a customer-managed encryption key where required by policy, or document provider-managed encryption approval.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "encryption_key_name": encryption_key or settings.get("encryption_key_name"),
        },
        ["cloud", "database", "gcp", "encryption"],
    )


def gcp_sql_private_connectivity_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_sql_database_instance":
        return None

    ip_config = cloud_sql_ip_configuration(config)
    if (
        ip_config.get("private_network")
        or ip_config.get("allocated_ip_range")
        or first_block(ip_config.get("psc_config")).get("psc_enabled") is True
    ):
        return None

    if config.get("private_connectivity_not_required") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.network.gcp.private_connectivity.missing",
        "operational_safety",
        "HIGH",
        f"GCP Cloud SQL instance '{resource.name}' lacks private connectivity evidence",
        "Cloud SQL instances without private connectivity evidence may depend on public IP paths, authorized networks, or unclear service access during production incidents.",
        "Configure private_network, Private Service Connect, or document an approved private-connectivity exception before production rollout.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "private_network": ip_config.get("private_network"),
            "allocated_ip_range": ip_config.get("allocated_ip_range"),
            "psc_config": first_block(ip_config.get("psc_config")),
            "ipv4_enabled": ip_config.get("ipv4_enabled"),
        },
        ["cloud", "gcp", "network", "private-connectivity"],
    )


def azure_key_vault_public_network_access_enabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "azurerm_key_vault":
        return None

    public_network_access = config.get("public_network_access_enabled")
    default_action = key_vault_default_action(config)

    if str(public_network_access).lower() in {"false", "disabled"} and default_action == "Deny":
        return None

    return build_cloud_finding(
        resource,
        "cloud.key_vault.azure.public_network_access.enabled",
        "operational_safety",
        "CRITICAL",
        f"Azure Key Vault '{resource.name}' allows public network access",
        "Public Key Vault access can expose secrets and keys to broader network attack paths.",
        "Disable public network access, set network ACL default_action to Deny, and require private endpoint access.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "public_network_access_enabled": public_network_access,
            "default_action": default_action,
        },
        ["cloud", "azure", "key-vault", "network"],
    )


def azure_key_vault_purge_protection_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "azurerm_key_vault":
        return None

    if config.get("purge_protection_enabled") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.key_vault.azure.purge_protection.disabled",
        "recovery_readiness",
        "HIGH",
        f"Azure Key Vault '{resource.name}' does not enable purge protection",
        "Without purge protection, accidental or malicious deletion can permanently remove secrets and keys.",
        "Enable purge_protection_enabled and validate recovery procedures for production vaults.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "purge_protection_enabled": config.get("purge_protection_enabled"),
        },
        ["cloud", "azure", "key-vault", "recovery"],
    )


def azure_private_endpoint_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_PRIVATE_ENDPOINT_TARGET_TYPES:
        return None

    if config.get("private_endpoint_not_required") is True:
        return None

    if has_matching_azure_private_endpoint(resource, context):
        return None

    return build_cloud_finding(
        resource,
        "cloud.network.azure.private_endpoint.missing",
        "operational_safety",
        "HIGH",
        f"Azure resource '{resource.name}' has no private endpoint evidence",
        "Sensitive Azure services without private endpoint evidence may rely on public network paths or unclear access controls.",
        "Add a private endpoint for production databases and Key Vaults, or document an approved exception with compensating controls.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "id": config.get("id"),
        },
        ["cloud", "azure", "private-endpoint"],
    )


def gcp_firewall_open_ingress(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_compute_firewall":
        return None

    direction = str(config.get("direction") or "INGRESS").upper()
    source_ranges = normalize_cidrs(config.get("source_ranges") or [])
    if direction != "INGRESS" or "0.0.0.0/0" not in source_ranges:
        return None

    return build_cloud_finding(
        resource,
        "cloud.network.gcp.firewall.open_ingress",
        "operational_safety",
        "HIGH",
        f"GCP firewall rule '{resource.name}' allows public ingress",
        "Public ingress firewall rules increase attack surface and can expose services directly to the internet.",
        "Restrict source_ranges to approved networks or front services with approved load balancing and WAF controls.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "source_ranges": source_ranges,
            "allowed": config.get("allow"),
        },
        ["cloud", "gcp", "network", "firewall"],
    )


def gke_private_nodes_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_container_cluster":
        return None

    private_config = first_block(config.get("private_cluster_config"))
    if private_config.get("enable_private_nodes") is True:
        return None

    return build_cloud_finding(
        resource,
        "cloud.kubernetes.gcp.private_nodes.disabled",
        "operational_safety",
        "HIGH",
        f"GKE cluster '{resource.name}' does not enable private nodes",
        "Publicly reachable worker nodes increase cluster attack surface and weaken network isolation.",
        "Enable private nodes for production GKE clusters or document an approved exception.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "enable_private_nodes": private_config.get("enable_private_nodes"),
        },
        ["cloud", "gcp", "gke", "network"],
    )


def gke_master_authorized_networks_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_container_cluster":
        return None

    if config.get("master_authorized_networks_config"):
        return None

    return build_cloud_finding(
        resource,
        "cloud.kubernetes.gcp.master_authorized_networks.missing",
        "operational_safety",
        "HIGH",
        f"GKE cluster '{resource.name}' has no master authorized networks",
        "A control plane without authorized network restrictions has weaker administrative access posture.",
        "Define master_authorized_networks_config for production clusters or use approved private control-plane access.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "master_authorized_networks_config_present": False,
        },
        ["cloud", "gcp", "gke", "control-plane"],
    )


def gke_regional_resiliency_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_container_cluster":
        return None

    regional = config.get("regional") is True
    location = str(config.get("location") or config.get("region") or config.get("zone") or "")
    node_locations = config.get("node_locations") or []
    if isinstance(node_locations, str):
        node_locations = [node_locations]

    # Terraform often uses a zone like us-central1-a for zonal clusters. A
    # regional cluster typically uses a region and multiple node locations.
    looks_zonal = location.count("-") >= 2
    if regional or len(node_locations) >= 2 or (location and not looks_zonal):
        return None

    return build_cloud_finding(
        resource,
        "cloud.kubernetes.gcp.regional_resiliency.missing",
        "resiliency",
        "HIGH",
        f"GKE cluster '{resource.name}' does not show regional resiliency",
        "A zonal or single-location GKE cluster has weaker tolerance for zone failure and node-pool disruption.",
        "Use a regional GKE cluster or multiple node locations for production workloads, or document an approved exception.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "location": location,
            "node_locations": node_locations,
            "regional": regional,
        },
        ["cloud", "gcp", "gke", "resiliency"],
    )


def azure_regional_resiliency_missing(resource, context):
    resources = [
        item
        for item in context.get("resources", [])
        if item.type == "cloud_resource"
        and str(item.attributes.get("provider_resource_type") or "").startswith("azurerm_")
        and item.attributes.get("provider_resource_type") != "azurerm_private_endpoint"
    ]

    if not resources:
        return None

    anchor = min(resources, key=lambda item: (item.source, item.name))
    if resource.name != anchor.name or resource.source != anchor.source:
        return None

    prod_resources = [
        item for item in resources if is_prod_like_cloud_config(item.attributes.get("config", {}))
    ]

    if len(prod_resources) < 2:
        return None

    locations = {
        normalized_location(item.attributes.get("config", {}))
        for item in prod_resources
        if normalized_location(item.attributes.get("config", {}))
    }

    if len(locations) != 1:
        return None

    subscriptions = {
        azure_subscription_id(item.attributes.get("config", {}))
        for item in prod_resources
        if azure_subscription_id(item.attributes.get("config", {}))
    }
    resource_groups = {
        azure_resource_group(item.attributes.get("config", {}))
        for item in prod_resources
        if azure_resource_group(item.attributes.get("config", {}))
    }

    return build_cloud_finding(
        resource,
        "cloud.region.azure.resiliency.missing",
        "resiliency",
        "HIGH",
        "Azure production resources are concentrated in one region",
        "Production Azure resources concentrated in one region have weaker disaster tolerance and can make regional outages or resource-group failures harder to survive.",
        "Distribute critical production resources across approved paired/secondary regions, or document an explicit single-region exception with recovery runbooks.",
        {
            "locations": sorted(locations),
            "subscriptions": sorted(subscriptions),
            "resource_groups": sorted(resource_groups),
            "prod_resource_count": len(prod_resources),
        },
        ["cloud", "azure", "resiliency", "multi-region"],
    )


def gcp_regional_dependency_concentration(resource, context):
    resources = [
        item
        for item in context.get("resources", [])
        if item.type in {"cloud_resource", "object_storage_bucket"}
        and str(item.attributes.get("provider_resource_type") or "").startswith("google_")
    ]

    if not resources:
        return None

    cloud_anchors = [item for item in resources if item.type == "cloud_resource"]
    if not cloud_anchors:
        return None

    anchor = min(cloud_anchors, key=lambda item: (item.source, item.name))
    if resource.name != anchor.name or resource.source != anchor.source:
        return None

    prod_resources = [
        item for item in resources if is_prod_like_cloud_config(item.attributes.get("config", {}))
    ]

    if len(prod_resources) < 3:
        return None

    regions = {
        normalized_gcp_region(item.attributes.get("config", {}))
        for item in prod_resources
        if normalized_gcp_region(item.attributes.get("config", {}))
    }

    if len(regions) != 1:
        return None

    resource_types = sorted(
        {
            item.attributes.get("provider_resource_type")
            for item in prod_resources
            if item.attributes.get("provider_resource_type")
        }
    )

    if not {"google_sql_database_instance", "google_container_cluster"} & set(resource_types):
        return None

    return build_cloud_finding(
        resource,
        "cloud.region.gcp.dependency_concentration",
        "resiliency",
        "HIGH",
        "GCP production dependencies are concentrated in one region",
        "Cloud SQL, GKE, storage, or network dependencies concentrated in one GCP region can turn a regional incident into a broad service outage.",
        "Distribute critical dependencies across approved regions or document a single-region exception with failover, backup, and recovery validation.",
        {
            "regions": sorted(regions),
            "resource_types": resource_types,
            "prod_resource_count": len(prod_resources),
        },
        ["cloud", "gcp", "resiliency", "multi-region"],
    )


def azure_vm_scale_set_headroom_insufficient(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in AZURE_VM_SCALE_SET_RESOURCE_TYPES:
        return None

    instances = first_present(config, "instances", "capacity", "sku_capacity")
    max_capacity = first_present(config, "max_capacity", "max_instances", "autoscale_max_capacity")

    if instances is None or max_capacity is None:
        return None

    if as_number(max_capacity) > as_number(instances):
        return None

    return build_cloud_finding(
        resource,
        "cloud.compute.azure.vmss.scale_headroom.insufficient",
        "scalability",
        "HIGH",
        f"Azure VM scale set '{resource.name}' has no scale-out headroom",
        "A VM scale set already at max capacity cannot absorb traffic spikes, node replacement, or rollout surge safely.",
        "Increase autoscale max capacity above current instances and validate subnet, quota, and load balancer capacity before production rollout.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "instances": instances,
            "max_capacity": max_capacity,
        },
        ["cloud", "azure", "compute", "autoscaling"],
    )


def provider_quota_headroom_insufficient(resource, context, expected_provider):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "cloud_quota_profile":
        return None

    provider = str(config.get("provider") or "").lower()
    if provider != expected_provider:
        return None

    quota_limit = config.get("quota_limit")
    required_capacity = config.get("required_capacity")
    reserved_buffer = config.get("reserved_buffer", 0)

    if quota_limit is None or required_capacity is None:
        return None

    if as_number(required_capacity) + as_number(reserved_buffer) <= as_number(quota_limit):
        return None

    provider_label = "Azure" if provider == "azure" else "GCP"
    rule_id = f"cloud.quota.{provider}.headroom.insufficient"

    return build_cloud_finding(
        resource,
        rule_id,
        "scalability",
        "CRITICAL",
        f"{provider_label} quota profile '{resource.name}' lacks deployment headroom",
        "Provider quota below required capacity plus buffer can block autoscaling, rollout surge, or incident recovery.",
        "Request quota increase, reduce requested capacity, or revise the safety buffer before production rollout.",
        {
            "resource_name": resource.name,
            "resource_type": resource_type,
            "provider": provider,
            "quota_limit": quota_limit,
            "required_capacity": required_capacity,
            "reserved_buffer": reserved_buffer,
        },
        ["cloud", provider, "quota", "capacity"],
    )


def azure_quota_headroom_insufficient(resource, context):
    return provider_quota_headroom_insufficient(resource, context, "azure")


def gcp_quota_headroom_insufficient(resource, context):
    return provider_quota_headroom_insufficient(resource, context, "gcp")


def key_vault_default_action(config):
    network_acls = first_block(config.get("network_acls"))
    return network_acls.get("default_action")


def has_matching_azure_private_endpoint(resource, context):
    config = resource.attributes.get("config", {})
    identifiers = {
        str(value).lower()
        for value in [
            resource.name,
            config.get("id"),
            config.get("name"),
        ]
        if value
    }

    endpoints = [
        item
        for item in context.get("resources", [])
        if item.attributes.get("provider_resource_type") == "azurerm_private_endpoint"
    ]
    for endpoint in endpoints:
        endpoint_config = endpoint.attributes.get("config", {})
        connections = endpoint_config.get("private_service_connection") or []
        for connection in ensure_list(connections):
            if not isinstance(connection, dict):
                continue
            connection_values = {
                str(value).lower()
                for value in [
                    connection.get("private_connection_resource_id"),
                    connection.get("name"),
                    connection.get("private_connection_resource_alias"),
                ]
                if value
            }
            if identifiers & connection_values:
                return True

    return False


def first_block(value):
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], dict) else {}
    return value if isinstance(value, dict) else {}


def ensure_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def first_present(config, *keys):
    for key in keys:
        if key in config:
            return config.get(key)
    return None


def is_prod_like_cloud_config(config):
    tags = config.get("tags") or config.get("labels") or {}
    markers = {
        config.get("environment"),
        config.get("env"),
        tags.get("environment") if isinstance(tags, dict) else None,
        tags.get("env") if isinstance(tags, dict) else None,
    }
    return any(str(value or "").lower() in {"prod", "production"} for value in markers)


def normalized_location(config):
    value = first_present(config, "location", "region")
    return str(value).lower() if value else None


def normalized_gcp_region(config):
    value = first_present(config, "region", "location")
    if not value:
        return None

    location = str(value).lower()
    pieces = location.split("-")
    if len(pieces) >= 3 and len(pieces[-1]) == 1 and pieces[-1].isalpha():
        return "-".join(pieces[:-1])
    return location


def azure_subscription_id(config):
    explicit = first_present(config, "subscription_id", "subscription")
    if explicit:
        return str(explicit)

    resource_id = str(config.get("id") or "")
    marker = "/subscriptions/"
    lowered = resource_id.lower()
    if marker not in lowered:
        return None

    start = lowered.index(marker) + len(marker)
    remainder = resource_id[start:]
    return remainder.split("/")[0] if remainder else None


def azure_resource_group(config):
    explicit = first_present(config, "resource_group_name", "resource_group")
    if explicit:
        return str(explicit)

    resource_id = str(config.get("id") or "")
    marker = "/resourcegroups/"
    lowered = resource_id.lower()
    if marker not in lowered:
        return None

    start = lowered.index(marker) + len(marker)
    remainder = resource_id[start:]
    return remainder.split("/")[0] if remainder else None


def as_number(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0
    return 0


def cloud_sql_settings(config):
    settings = config.get("settings") or {}
    if isinstance(settings, list):
        return settings[0] if settings and isinstance(settings[0], dict) else {}
    return settings if isinstance(settings, dict) else {}


def cloud_sql_ip_configuration(config):
    settings = cloud_sql_settings(config)
    ip_config = settings.get("ip_configuration") or {}
    if isinstance(ip_config, list):
        return ip_config[0] if ip_config and isinstance(ip_config[0], dict) else {}
    return ip_config if isinstance(ip_config, dict) else {}


def cloud_sql_backup_configuration(config):
    settings = cloud_sql_settings(config)
    backup_config = settings.get("backup_configuration") or {}
    if isinstance(backup_config, list):
        return backup_config[0] if backup_config and isinstance(backup_config[0], dict) else {}
    return backup_config if isinstance(backup_config, dict) else {}


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
    "terraform.plan.unknown_after_apply.correlation_gap",
    "operational_safety",
    "MEDIUM",
    "Terraform unknown-after-apply correlation gap",
    "Detects Terraform plan values that remain unknown until apply and reduce dependency-correlation confidence.",
    terraform_unknown_after_apply_correlation_gap,
    ["terraform", "plan", "unknown-after-apply", "correlation"],
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
    "cloud.database.rds.deletion_protection.disabled",
    "recovery_readiness",
    "HIGH",
    "RDS deletion protection disabled",
    "Detects RDS instances without deletion protection.",
    rds_deletion_protection_disabled,
    ["cloud", "database", "rds", "recovery"],
)
register(
    "cloud.database.rds.storage_encryption.disabled",
    "operational_safety",
    "HIGH",
    "RDS storage encryption disabled",
    "Detects RDS instances without storage encryption.",
    rds_storage_encryption_disabled,
    ["cloud", "database", "rds", "encryption"],
)

register(
    "cloud.database.azure.public_network_access.enabled",
    "operational_safety",
    "CRITICAL",
    "Azure database public network access enabled",
    "Detects Azure managed databases with public network access enabled.",
    azure_database_public_access_enabled,
    ["cloud", "database", "azure", "network"],
)
register(
    "cloud.database.azure.backup_retention.weak",
    "recovery_readiness",
    "HIGH",
    "Azure database backup retention weak",
    "Detects Azure managed databases with missing or weak backup retention.",
    azure_database_backup_retention_weak,
    ["cloud", "database", "azure", "backup"],
)
register(
    "cloud.database.azure.ha.disabled",
    "resiliency",
    "HIGH",
    "Azure database HA disabled",
    "Detects Azure managed databases without high-availability posture.",
    azure_database_ha_disabled,
    ["cloud", "database", "azure", "ha"],
)
register(
    "cloud.database.azure.deletion_protection.missing",
    "recovery_readiness",
    "HIGH",
    "Azure database deletion protection missing",
    "Detects Azure managed databases without deletion-protection or prevent-destroy evidence.",
    azure_database_deletion_protection_missing,
    ["cloud", "database", "azure", "recovery"],
)
register(
    "cloud.database.azure.customer_managed_key.missing",
    "operational_safety",
    "MEDIUM",
    "Azure database customer-managed key missing",
    "Detects Azure managed databases without customer-managed key evidence.",
    azure_database_customer_managed_key_missing,
    ["cloud", "database", "azure", "encryption"],
)
register(
    "cloud.database.gcp.public_ip.enabled",
    "operational_safety",
    "CRITICAL",
    "GCP Cloud SQL public IP enabled",
    "Detects GCP Cloud SQL instances with public IP or authorized networks.",
    gcp_sql_public_access_enabled,
    ["cloud", "database", "gcp", "network"],
)
register(
    "cloud.database.gcp.backup.disabled",
    "recovery_readiness",
    "HIGH",
    "GCP Cloud SQL backups disabled",
    "Detects GCP Cloud SQL instances without backup configuration enabled.",
    gcp_sql_backup_disabled,
    ["cloud", "database", "gcp", "backup"],
)
register(
    "cloud.database.gcp.deletion_protection.disabled",
    "recovery_readiness",
    "HIGH",
    "GCP Cloud SQL deletion protection disabled",
    "Detects GCP Cloud SQL instances without deletion protection.",
    gcp_sql_deletion_protection_disabled,
    ["cloud", "database", "gcp", "recovery"],
)
register(
    "cloud.database.gcp.ha.disabled",
    "resiliency",
    "HIGH",
    "GCP Cloud SQL HA disabled",
    "Detects GCP Cloud SQL instances without regional high availability.",
    gcp_sql_ha_disabled,
    ["cloud", "database", "gcp", "ha"],
)
register(
    "cloud.database.gcp.cmek.missing",
    "operational_safety",
    "MEDIUM",
    "GCP Cloud SQL CMEK missing",
    "Detects GCP Cloud SQL instances without customer-managed encryption key evidence.",
    gcp_sql_customer_managed_encryption_missing,
    ["cloud", "database", "gcp", "encryption"],
)
register(
    "cloud.network.gcp.private_connectivity.missing",
    "operational_safety",
    "HIGH",
    "GCP private connectivity missing",
    "Detects Cloud SQL instances without private_network or Private Service Connect evidence.",
    gcp_sql_private_connectivity_missing,
    ["cloud", "gcp", "network", "private-connectivity"],
)
register(
    "cloud.key_vault.azure.public_network_access.enabled",
    "operational_safety",
    "CRITICAL",
    "Azure Key Vault public network access enabled",
    "Detects Azure Key Vaults with public network access or permissive network ACLs.",
    azure_key_vault_public_network_access_enabled,
    ["cloud", "azure", "key-vault", "network"],
)
register(
    "cloud.key_vault.azure.purge_protection.disabled",
    "recovery_readiness",
    "HIGH",
    "Azure Key Vault purge protection disabled",
    "Detects Azure Key Vaults without purge protection.",
    azure_key_vault_purge_protection_disabled,
    ["cloud", "azure", "key-vault", "recovery"],
)
register(
    "cloud.network.azure.private_endpoint.missing",
    "operational_safety",
    "HIGH",
    "Azure private endpoint missing",
    "Detects sensitive Azure managed services without private endpoint evidence.",
    azure_private_endpoint_missing,
    ["cloud", "azure", "private-endpoint"],
)
register(
    "cloud.network.gcp.firewall.open_ingress",
    "operational_safety",
    "HIGH",
    "GCP firewall public ingress",
    "Detects GCP firewall rules with public ingress source ranges.",
    gcp_firewall_open_ingress,
    ["cloud", "gcp", "network", "firewall"],
)
register(
    "cloud.kubernetes.gcp.private_nodes.disabled",
    "operational_safety",
    "HIGH",
    "GKE private nodes disabled",
    "Detects GKE clusters without private nodes.",
    gke_private_nodes_disabled,
    ["cloud", "gcp", "gke", "network"],
)
register(
    "cloud.kubernetes.gcp.master_authorized_networks.missing",
    "operational_safety",
    "HIGH",
    "GKE master authorized networks missing",
    "Detects GKE clusters without master authorized networks.",
    gke_master_authorized_networks_missing,
    ["cloud", "gcp", "gke", "control-plane"],
)
register(
    "cloud.kubernetes.gcp.regional_resiliency.missing",
    "resiliency",
    "HIGH",
    "GKE regional resiliency missing",
    "Detects GKE clusters without regional or multi-zone resiliency evidence.",
    gke_regional_resiliency_missing,
    ["cloud", "gcp", "gke", "resiliency"],
)
register(
    "cloud.region.azure.resiliency.missing",
    "resiliency",
    "HIGH",
    "Azure regional resiliency missing",
    "Detects production Azure resource sets concentrated in a single region.",
    azure_regional_resiliency_missing,
    ["cloud", "azure", "resiliency", "multi-region"],
)
register(
    "cloud.region.gcp.dependency_concentration",
    "resiliency",
    "HIGH",
    "GCP regional dependency concentration",
    "Detects production GCP dependency sets concentrated in one region.",
    gcp_regional_dependency_concentration,
    ["cloud", "gcp", "resiliency", "multi-region"],
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
    "cloud.compute.azure.vmss.scale_headroom.insufficient",
    "scalability",
    "HIGH",
    "Azure VM scale set headroom insufficient",
    "Detects Azure VM scale sets without scale-out headroom.",
    azure_vm_scale_set_headroom_insufficient,
    ["cloud", "azure", "compute", "autoscaling"],
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
    "cloud.quota.azure.headroom.insufficient",
    "scalability",
    "CRITICAL",
    "Azure quota headroom insufficient",
    "Detects Azure quota profiles that cannot satisfy requested capacity plus buffer.",
    azure_quota_headroom_insufficient,
    ["cloud", "azure", "quota", "capacity"],
)
register(
    "cloud.quota.gcp.headroom.insufficient",
    "scalability",
    "CRITICAL",
    "GCP quota headroom insufficient",
    "Detects GCP quota profiles that cannot satisfy requested capacity plus buffer.",
    gcp_quota_headroom_insufficient,
    ["cloud", "gcp", "quota", "capacity"],
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
