def finding(severity, title, impact, recommendation, file):
    return {
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file
    }


# =========================================================
# Kafka Rules
# =========================================================

def evaluate_kafka_config(data, file):
    findings = []

    topics = data.get("topics", [])

    for topic in topics:
        name = topic.get("name", "unknown-topic")

        rf = topic.get("replication_factor")
        partitions = topic.get("partitions")
        retention_ms = topic.get("retention_ms")
        cleanup_policy = topic.get("cleanup_policy")
        min_isr = topic.get("min_insync_replicas")

        # Replication factor
        if rf is not None and rf < 3:
            findings.append(finding(
                "CRITICAL",
                f"Kafka topic '{name}' has replication factor {rf}",
                "A broker failure can make this topic unavailable and interrupt production workflows.",
                "Use replication_factor=3 for production topics.",
                file
            ))

        # Partition count
        if partitions is not None and partitions < 3:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' has low partition count",
                "Low partitions can limit consumer parallelism and reduce throughput.",
                "Use at least 3 partitions for production workloads.",
                file
            ))

        # Retention
        if retention_ms is not None and retention_ms < 86400000:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' retention is below 24 hours",
                "Short retention reduces replay capability during incidents.",
                "Increase retention based on recovery and audit requirements.",
                file
            ))

        # Cleanup policy
        if cleanup_policy is None:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' does not define cleanup policy",
                "Undefined cleanup policy may create unpredictable retention behavior.",
                "Explicitly configure cleanup_policy.",
                file
            ))

        # Min ISR
        if min_isr is None:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' does not define min.insync.replicas",
                "Missing min ISR configuration can weaken durability guarantees during broker failure.",
                "Configure min.insync.replicas for production topics.",
                file
            ))

    return findings


# =========================================================
# Terraform Rules
# =========================================================

def evaluate_terraform_config(data, file):
    findings = []

    resources = data.get("resource", [])

    for block in resources:
        for resource_type, instances in block.items():

            # AWS S3 public access block
            if resource_type == "aws_s3_bucket_public_access_block":
                for name, config in instances.items():
                    if (
                        config.get("block_public_acls") is False
                        or config.get("block_public_policy") is False
                        or config.get("ignore_public_acls") is False
                        or config.get("restrict_public_buckets") is False
                    ):
                        findings.append(finding(
                            "CRITICAL",
                            f"Object storage public access protection is weak: {name}",
                            "Public object storage exposure can lead to sensitive data leakage.",
                            "Block public access unless there is an explicit approved exception.",
                            file
                        ))

            # AWS S3 bucket
            if resource_type == "aws_s3_bucket":
                for name, config in instances.items():

                    if "server_side_encryption_configuration" not in config:
                        findings.append(finding(
                            "HIGH",
                            f"Object storage bucket '{name}' does not enable encryption",
                            "Unencrypted object storage may violate security and compliance requirements.",
                            "Enable provider-managed or customer-managed encryption.",
                            file
                        ))

                    if "versioning" not in config:
                        findings.append(finding(
                            "MEDIUM",
                            f"Object storage bucket '{name}' does not enable versioning",
                            "Without versioning, accidental deletion or overwrite recovery becomes difficult.",
                            "Enable object versioning for production workloads.",
                            file
                        ))

                    if "tags" not in config:
                        findings.append(finding(
                            "LOW",
                            f"Object storage bucket '{name}' is missing tags",
                            "Missing tags reduce ownership tracking, governance, and cost visibility.",
                            "Add standard ownership, environment, and application tags.",
                            file
                        ))

            # GCP Cloud Storage bucket
            if resource_type == "google_storage_bucket":
                for name, config in instances.items():

                    if config.get("uniform_bucket_level_access") is not True:
                        findings.append(finding(
                            "HIGH",
                            f"GCP storage bucket '{name}' does not enforce uniform bucket-level access",
                            "Object-level ACLs can create inconsistent and hard-to-audit access behavior.",
                            "Enable uniform_bucket_level_access for production buckets.",
                            file
                        ))

                    if "versioning" not in config:
                        findings.append(finding(
                            "MEDIUM",
                            f"GCP storage bucket '{name}' does not enable versioning",
                            "Without versioning, accidental deletion or overwrite recovery becomes difficult.",
                            "Enable versioning for critical production buckets.",
                            file
                        ))

                    if "labels" not in config:
                        findings.append(finding(
                            "LOW",
                            f"GCP storage bucket '{name}' is missing labels",
                            "Missing labels reduce ownership tracking, governance, and cost visibility.",
                            "Add standard ownership, environment, and application labels.",
                            file
                        ))

            # Azure Storage Account
            if resource_type == "azurerm_storage_account":
                for name, config in instances.items():

                    if config.get("allow_blob_public_access") is not False:
                        findings.append(finding(
                            "CRITICAL",
                            f"Azure storage account '{name}' may allow public blob access",
                            "Public blob access can expose sensitive data unintentionally.",
                            "Set allow_blob_public_access=false for production storage accounts.",
                            file
                        ))

                    if config.get("infrastructure_encryption_enabled") is not True:
                        findings.append(finding(
                            "HIGH",
                            f"Azure storage account '{name}' does not enable infrastructure encryption",
                            "Weak encryption posture may violate production security requirements.",
                            "Enable infrastructure encryption for sensitive production workloads.",
                            file
                        ))

                    if "tags" not in config:
                        findings.append(finding(
                            "LOW",
                            f"Azure storage account '{name}' is missing tags",
                            "Missing tags reduce ownership tracking, governance, and cost visibility.",
                            "Add standard ownership, environment, and application tags.",
                            file
                        ))

            # IAM / permission wildcard — generic cloud risk
            if resource_type in ["aws_iam_policy", "google_project_iam_binding", "azurerm_role_assignment"]:
                for name, config in instances.items():
                    raw_config = str(config)

                    if (
                        '"Action":"*"' in raw_config
                        or '"Resource":"*"' in raw_config
                        or "*:*" in raw_config
                        or "roles/owner" in raw_config
                        or "Owner" in raw_config
                    ):
                        findings.append(finding(
                            "HIGH",
                            f"Over-permissive cloud access detected in '{name}'",
                            "Broad permissions increase blast radius during credential misuse or accidental changes.",
                            "Apply least-privilege permissions and avoid owner/admin-level access unless justified.",
                            file
                        ))

    return findings