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
        retention_bytes = topic.get("retention_bytes")
        cleanup_policy = topic.get("cleanup_policy")
        min_isr = topic.get("min_insync_replicas")
        segment_bytes = topic.get("segment_bytes")
        max_message_bytes = topic.get("max_message_bytes")

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

        # Retention time
        if retention_ms is not None and retention_ms < 86400000:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' retention is below 24 hours",
                "Short retention reduces replay capability during incidents.",
                "Increase retention based on recovery and audit requirements.",
                file
            ))

        # Missing cleanup policy
        if cleanup_policy is None:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' does not define cleanup policy",
                "Undefined cleanup policy may create unpredictable retention and disk behavior.",
                "Explicitly configure cleanup_policy as delete, compact, or compact,delete.",
                file
            ))

        # Missing min ISR
        if min_isr is None:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' does not define min.insync.replicas",
                "Missing min ISR configuration can weaken durability guarantees during broker failure.",
                "Configure min.insync.replicas for production topics.",
                file
            ))

        # Missing retention bytes
        if retention_bytes is None:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' does not define retention_bytes",
                "Disk usage can grow unpredictably if producer volume increases or cleanup is delayed.",
                "Set retention_bytes based on broker disk capacity, expected throughput, and recovery needs.",
                file
            ))

        # High storage multiplier
        if rf is not None and partitions is not None:
            storage_units = rf * partitions

            if storage_units >= 30:
                findings.append(finding(
                    "HIGH",
                    f"Kafka topic '{name}' has high storage multiplier: partitions({partitions}) x replication_factor({rf}) = {storage_units}",
                    "High partition and replica count increases broker disk usage, replication traffic, and recovery load.",
                    "Validate broker disk capacity, partition distribution, and expected data volume.",
                    file
                ))

            elif storage_units >= 15:
                findings.append(finding(
                    "MEDIUM",
                    f"Kafka topic '{name}' has moderate storage multiplier: partitions({partitions}) x replication_factor({rf}) = {storage_units}",
                    "Replica storage grows with every partition and can increase disk pressure during traffic spikes.",
                    "Review whether partition count and replication factor match actual throughput needs.",
                    file
                ))

        # Large message size risk
        if max_message_bytes is not None and max_message_bytes > 1048576:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' allows messages larger than 1MB",
                "Large messages increase broker disk I/O, memory pressure, network usage, and consumer processing latency.",
                "Keep Kafka messages small where possible; store large payloads externally and pass references through Kafka.",
                file
            ))

        # Very large segment size risk
        if segment_bytes is not None and segment_bytes > 1073741824:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' has segment_bytes greater than 1GB",
                "Large log segments can delay cleanup and make disk recovery behavior less predictable.",
                "Use segment size based on retention, cleanup frequency, and operational recovery needs.",
                file
            ))

        # Compacted topic without delete policy
        if cleanup_policy == "compact" and retention_bytes is None:
            findings.append(finding(
                "MEDIUM",
                f"Kafka compacted topic '{name}' has no retention_bytes limit",
                "Compacted topics can still consume significant disk if key cardinality is high or tombstone cleanup is delayed.",
                "Set retention_bytes or review compaction and key cardinality assumptions.",
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