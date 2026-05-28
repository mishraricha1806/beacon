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
        domain="object_storage",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def public_access_enabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    offending_keys = []

    if resource_type == "aws_s3_bucket_public_access_block":
        checks = [
            "block_public_acls",
            "block_public_policy",
            "ignore_public_acls",
            "restrict_public_buckets",
        ]

        for key in checks:
            if config.get(key) is False:
                offending_keys.append(key)

    if resource_type == "azurerm_storage_account":
        if config.get("allow_blob_public_access") is not False:
            offending_keys.append("allow_blob_public_access")

    if not offending_keys:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="object_storage.public_access.enabled",
        category="operational_safety",
        severity="CRITICAL",
        title=f"Object storage public access protection is weak: {resource.name}",
        impact="Public object storage exposure can lead to sensitive data leakage.",
        recommendation="Block public access unless there is an explicit approved exception.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "offending_keys": offending_keys,
        },
        tags=["storage", "security", "public-access"],
    )


def encryption_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    missing = False

    if resource_type == "aws_s3_bucket":
        missing = "server_side_encryption_configuration" not in config

    if resource_type == "azurerm_storage_account":
        missing = config.get("infrastructure_encryption_enabled") is not True

    if not missing:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="object_storage.encryption.missing",
        category="operational_safety",
        severity="HIGH",
        title=f"Object storage resource '{resource.name}' does not enable encryption",
        impact="Weak encryption posture may violate production security requirements.",
        recommendation="Enable provider-managed or customer-managed encryption.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "encryption_present": False,
        },
        tags=["storage", "security", "encryption"],
    )


def versioning_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in {"aws_s3_bucket", "google_storage_bucket"}:
        return None

    if "versioning" in config:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="object_storage.versioning.missing",
        category="recovery_readiness",
        severity="MEDIUM",
        title=f"Object storage resource '{resource.name}' does not enable versioning",
        impact="Without versioning, accidental deletion or overwrite recovery becomes difficult.",
        recommendation="Enable versioning for critical production object storage.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "versioning_present": False,
        },
        tags=["storage", "recovery", "versioning"],
    )


def lifecycle_policy_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "aws_s3_bucket":
        return None

    if "lifecycle_rule" in config or "lifecycle_configuration" in config:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="object_storage.lifecycle_policy.missing",
        category="storage_sustainability",
        severity="MEDIUM",
        title=f"Object storage bucket '{resource.name}' does not define lifecycle policy",
        impact="Without lifecycle policy, old objects may accumulate and increase storage cost.",
        recommendation="Define lifecycle rules for expiration, archival, or cleanup.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "lifecycle_policy_present": False,
        },
        tags=["storage", "lifecycle", "cost"],
    )


def labels_or_tags_missing(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type in {"aws_s3_bucket", "azurerm_storage_account"}:
        missing = "tags" not in config
        label_name = "tags"
    elif resource_type == "google_storage_bucket":
        missing = "labels" not in config
        label_name = "labels"
    else:
        return None

    if not missing:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="object_storage.labels_or_tags.missing",
        category="operational_safety",
        severity="LOW",
        title=f"Object storage resource '{resource.name}' is missing {label_name}",
        impact="Missing ownership metadata reduces governance and cost visibility.",
        recommendation="Add standard ownership, environment, and application metadata.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            f"{label_name}_present": False,
        },
        tags=["storage", "governance", "ownership"],
    )


def gcp_uniform_bucket_access_disabled(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type != "google_storage_bucket":
        return None

    if config.get("uniform_bucket_level_access") is True:
        return None

    return build_storage_finding(
        resource=resource,
        rule_id="gcp.storage.uniform_bucket_access.disabled",
        category="operational_safety",
        severity="HIGH",
        title=f"GCP storage bucket '{resource.name}' does not enforce uniform bucket-level access",
        impact="Object-level ACLs can create inconsistent and hard-to-audit access behavior.",
        recommendation="Enable uniform_bucket_level_access for production buckets.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "uniform_bucket_level_access": config.get("uniform_bucket_level_access"),
        },
        tags=["gcp", "storage", "access-control"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="object_storage",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["object_storage_bucket"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "object_storage.public_access.enabled",
    "operational_safety",
    "CRITICAL",
    "Object storage public access enabled",
    "Detects object storage resources with public access exposure.",
    public_access_enabled,
    ["storage", "security", "public-access"],
)

register(
    "object_storage.encryption.missing",
    "operational_safety",
    "HIGH",
    "Object storage encryption missing",
    "Detects object storage resources without encryption.",
    encryption_missing,
    ["storage", "security", "encryption"],
)

register(
    "object_storage.versioning.missing",
    "recovery_readiness",
    "MEDIUM",
    "Object storage versioning missing",
    "Detects object storage resources without versioning.",
    versioning_missing,
    ["storage", "recovery", "versioning"],
)

register(
    "object_storage.lifecycle_policy.missing",
    "storage_sustainability",
    "MEDIUM",
    "Object storage lifecycle policy missing",
    "Detects object storage resources without lifecycle policy.",
    lifecycle_policy_missing,
    ["storage", "lifecycle", "cost"],
)

register(
    "object_storage.labels_or_tags.missing",
    "operational_safety",
    "LOW",
    "Object storage ownership metadata missing",
    "Detects object storage resources without labels or tags.",
    labels_or_tags_missing,
    ["storage", "governance", "ownership"],
)

register(
    "gcp.storage.uniform_bucket_access.disabled",
    "operational_safety",
    "HIGH",
    "GCP uniform bucket access disabled",
    "Detects GCP buckets without uniform bucket-level access.",
    gcp_uniform_bucket_access_disabled,
    ["gcp", "storage", "access-control"],
)
