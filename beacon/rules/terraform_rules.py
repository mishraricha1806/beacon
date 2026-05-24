from beacon.rules.models import finding


def evaluate_terraform_config(data, file):
    findings = []
    resources = data.get("resource", [])

    for block in resources:
        for resource_type, instances in block.items():
            findings.extend(
                evaluate_object_storage(
                    resource_type,
                    instances,
                    file,
                )
            )

            findings.extend(
                evaluate_cloud_permissions(
                    resource_type,
                    instances,
                    file,
                )
            )

    return findings


def evaluate_object_storage(resource_type, instances, file):
    findings = []

    if resource_type == "aws_s3_bucket_public_access_block":
        for name, config in instances.items():

            offending_keys = []

            if config.get("block_public_acls") is False:
                offending_keys.append("block_public_acls")

            if config.get("block_public_policy") is False:
                offending_keys.append("block_public_policy")

            if config.get("ignore_public_acls") is False:
                offending_keys.append("ignore_public_acls")

            if config.get("restrict_public_buckets") is False:
                offending_keys.append("restrict_public_buckets")

            if offending_keys:
                findings.append(
                    finding(
                        rule_id="object_storage.public_access.enabled",
                        domain="object_storage",
                        category="operational_safety",
                        severity="CRITICAL",
                        title=(
                            f"Object storage public access protection is weak: {name}"
                        ),
                        impact=(
                            "Public object storage exposure can lead to "
                            "sensitive data leakage."
                        ),
                        recommendation=(
                            "Block public access unless there is an "
                            "explicit approved exception."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "offending_keys": offending_keys,
                            "block_public_acls": config.get("block_public_acls"),
                            "block_public_policy": config.get("block_public_policy"),
                            "ignore_public_acls": config.get("ignore_public_acls"),
                            "restrict_public_buckets": config.get(
                                "restrict_public_buckets"
                            ),
                        },
                        tags=[
                            "security",
                            "storage",
                            "public-access",
                        ],
                    )
                )

    if resource_type == "aws_s3_bucket":
        for name, config in instances.items():

            if "server_side_encryption_configuration" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.encryption.missing",
                        domain="object_storage",
                        category="operational_safety",
                        severity="HIGH",
                        title=(
                            f"Object storage bucket '{name}' "
                            "does not enable encryption"
                        ),
                        impact=(
                            "Unencrypted object storage may violate "
                            "security and compliance requirements."
                        ),
                        recommendation=(
                            "Enable provider-managed or " "customer-managed encryption."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "encryption_present": False,
                        },
                        tags=[
                            "security",
                            "encryption",
                            "storage",
                        ],
                    )
                )

            if "versioning" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.versioning.missing",
                        domain="object_storage",
                        category="recovery_readiness",
                        severity="MEDIUM",
                        title=(
                            f"Object storage bucket '{name}' "
                            "does not enable versioning"
                        ),
                        impact=(
                            "Without versioning, accidental deletion "
                            "or overwrite recovery becomes difficult."
                        ),
                        recommendation=(
                            "Enable bucket versioning for " "production workloads."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "versioning_present": False,
                        },
                        tags=[
                            "recovery",
                            "storage",
                            "versioning",
                        ],
                    )
                )

            if (
                "lifecycle_rule" not in config
                and "lifecycle_configuration" not in config
            ):
                findings.append(
                    finding(
                        rule_id="object_storage.lifecycle_policy.missing",
                        domain="object_storage",
                        category="storage_sustainability",
                        severity="MEDIUM",
                        title=(
                            f"Object storage bucket '{name}' "
                            "does not define lifecycle policy"
                        ),
                        impact=(
                            "Without lifecycle policy, old objects may "
                            "accumulate and increase storage cost."
                        ),
                        recommendation=(
                            "Define lifecycle rules for expiration, "
                            "archival, or cleanup."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "lifecycle_policy_present": False,
                        },
                        tags=[
                            "storage",
                            "lifecycle",
                            "cost",
                        ],
                    )
                )

            if "tags" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.labels_or_tags.missing",
                        domain="object_storage",
                        category="operational_safety",
                        severity="LOW",
                        title=(f"Object storage bucket '{name}' " "is missing tags"),
                        impact=(
                            "Missing tags reduce ownership tracking, "
                            "governance, and cost visibility."
                        ),
                        recommendation=(
                            "Add standard ownership, environment, "
                            "and application tags."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "tags_present": False,
                        },
                        tags=[
                            "governance",
                            "cost",
                            "ownership",
                        ],
                    )
                )

    if resource_type == "google_storage_bucket":
        for name, config in instances.items():

            if config.get("uniform_bucket_level_access") is not True:
                findings.append(
                    finding(
                        rule_id=("gcp.storage.uniform_bucket_access.disabled"),
                        domain="object_storage",
                        category="operational_safety",
                        severity="HIGH",
                        title=(
                            f"GCP storage bucket '{name}' does not enforce "
                            "uniform bucket-level access"
                        ),
                        impact=(
                            "Object-level ACLs can create inconsistent "
                            "and hard-to-audit access behavior."
                        ),
                        recommendation=(
                            "Enable uniform_bucket_level_access "
                            "for production buckets."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "uniform_bucket_level_access": config.get(
                                "uniform_bucket_level_access"
                            ),
                        },
                        tags=[
                            "gcp",
                            "security",
                            "access-control",
                        ],
                    )
                )

            if "versioning" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.versioning.missing",
                        domain="object_storage",
                        category="recovery_readiness",
                        severity="MEDIUM",
                        title=(
                            f"GCP storage bucket '{name}' " "does not enable versioning"
                        ),
                        impact=(
                            "Without versioning, accidental deletion "
                            "or overwrite recovery becomes difficult."
                        ),
                        recommendation=(
                            "Enable versioning for " "critical production buckets."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "versioning_present": False,
                        },
                        tags=[
                            "gcp",
                            "recovery",
                            "storage",
                        ],
                    )
                )

            if "labels" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.labels_or_tags.missing",
                        domain="object_storage",
                        category="operational_safety",
                        severity="LOW",
                        title=(f"GCP storage bucket '{name}' " "is missing labels"),
                        impact=(
                            "Missing labels reduce ownership tracking, "
                            "governance, and cost visibility."
                        ),
                        recommendation=(
                            "Add standard ownership, environment, "
                            "and application labels."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "labels_present": False,
                        },
                        tags=[
                            "gcp",
                            "governance",
                            "cost",
                        ],
                    )
                )

    if resource_type == "azurerm_storage_account":
        for name, config in instances.items():

            if config.get("allow_blob_public_access") is not False:
                findings.append(
                    finding(
                        rule_id="object_storage.public_access.enabled",
                        domain="object_storage",
                        category="operational_safety",
                        severity="CRITICAL",
                        title=(
                            f"Azure storage account '{name}' "
                            "may allow public blob access"
                        ),
                        impact=(
                            "Public blob access can expose "
                            "sensitive data unintentionally."
                        ),
                        recommendation=(
                            "Set allow_blob_public_access=false "
                            "for production storage accounts."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "allow_blob_public_access": config.get(
                                "allow_blob_public_access"
                            ),
                        },
                        tags=[
                            "azure",
                            "security",
                            "public-access",
                        ],
                    )
                )

            if config.get("infrastructure_encryption_enabled") is not True:
                findings.append(
                    finding(
                        rule_id="object_storage.encryption.missing",
                        domain="object_storage",
                        category="operational_safety",
                        severity="HIGH",
                        title=(
                            f"Azure storage account '{name}' "
                            "does not enable infrastructure encryption"
                        ),
                        impact=(
                            "Weak encryption posture may violate "
                            "production security requirements."
                        ),
                        recommendation=(
                            "Enable infrastructure encryption "
                            "for sensitive production workloads."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "infrastructure_encryption_enabled": config.get(
                                "infrastructure_encryption_enabled"
                            ),
                        },
                        tags=[
                            "azure",
                            "encryption",
                            "security",
                        ],
                    )
                )

            if "tags" not in config:
                findings.append(
                    finding(
                        rule_id="object_storage.labels_or_tags.missing",
                        domain="object_storage",
                        category="operational_safety",
                        severity="LOW",
                        title=(f"Azure storage account '{name}' " "is missing tags"),
                        impact=(
                            "Missing tags reduce ownership tracking, "
                            "governance, and cost visibility."
                        ),
                        recommendation=(
                            "Add standard ownership, environment, "
                            "and application tags."
                        ),
                        file=file,
                        evidence={
                            "resource_type": resource_type,
                            "resource_name": name,
                            "tags_present": False,
                        },
                        tags=[
                            "azure",
                            "governance",
                            "cost",
                        ],
                    )
                )

    return findings


def evaluate_cloud_permissions(resource_type, instances, file):
    findings = []

    permission_resources = [
        "aws_iam_policy",
        "google_project_iam_binding",
        "azurerm_role_assignment",
    ]

    if resource_type not in permission_resources:
        return findings

    for name, config in instances.items():
        raw_config = str(config)

        if (
            '"Action":"*"' in raw_config
            or '"Resource":"*"' in raw_config
            or "*:*" in raw_config
        ):
            findings.append(
                finding(
                    rule_id="iam.permissions.wildcard",
                    domain="cloud_identity",
                    category="operational_safety",
                    severity="HIGH",
                    title=(f"Wildcard IAM permissions detected in '{name}'"),
                    impact=(
                        "Wildcard permissions increase blast radius "
                        "during credential misuse."
                    ),
                    recommendation=(
                        "Apply least-privilege permissions and "
                        "avoid wildcard access."
                    ),
                    file=file,
                    evidence={
                        "resource_type": resource_type,
                        "resource_name": name,
                        "pattern": "wildcard_permission",
                    },
                    tags=[
                        "iam",
                        "security",
                        "least-privilege",
                    ],
                )
            )

        if (
            "roles/owner" in raw_config
            or "Owner" in raw_config
            or "AdministratorAccess" in raw_config
        ):
            findings.append(
                finding(
                    rule_id="iam.admin_or_owner.excessive",
                    domain="cloud_identity",
                    category="operational_safety",
                    severity="HIGH",
                    title=(f"Administrative cloud access detected in '{name}'"),
                    impact=(
                        "Owner/admin-level access increases "
                        "operational blast radius."
                    ),
                    recommendation=(
                        "Restrict admin access to approved "
                        "platform administrators only."
                    ),
                    file=file,
                    evidence={
                        "resource_type": resource_type,
                        "resource_name": name,
                        "pattern": "admin_or_owner_access",
                    },
                    tags=[
                        "iam",
                        "security",
                        "admin-access",
                    ],
                )
            )

    return findings
