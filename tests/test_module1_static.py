"""Tests for MODULE 1: Static Infrastructure Analysis.

Covers:
- Kafka configuration analysis
- Terraform infrastructure review
- Storage and IAM security checks
- Operational anti-pattern detection
"""

import pytest
from beacon.rules import evaluate_kafka_config, evaluate_terraform_config, finding
from beacon.reporter import calculate_score


class TestKafkaStaticAnalysis:
    """Test static Kafka configuration analysis."""

    def test_replication_factor_critical(self):
        """Test detection of low replication factor (CRITICAL)."""
        data = {
            "topics": [
                {
                    "name": "payments",
                    "replication_factor": 1,
                    "partitions": 3,
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert len(findings) > 0
        assert any(f["severity"] == "CRITICAL" for f in findings)
        assert any("replication factor" in f["title"].lower() for f in findings)

    def test_low_partition_count(self):
        """Test detection of low partition count (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "events",
                    "replication_factor": 3,
                    "partitions": 1,
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any(f["severity"] == "HIGH" for f in findings)
        assert any("partition" in f["title"].lower() for f in findings)

    def test_missing_retention_bytes(self):
        """Test detection of missing retention_bytes (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "orders",
                    "replication_factor": 3,
                    "partitions": 3,
                    "retention_ms": 604800000,
                    # Missing retention_bytes
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any(f["severity"] == "HIGH" and "retention_bytes" in f["title"] for f in findings)

    def test_missing_min_isr(self):
        """Test detection of missing min ISR (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "critical",
                    "replication_factor": 3,
                    "partitions": 3,
                    # Missing min_insync_replicas
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any("min.insync.replicas" in f["title"] for f in findings)

    def test_unbounded_retention(self):
        """Test detection of unbounded retention (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "logs",
                    "replication_factor": 3,
                    "partitions": 3,
                    "retention_ms": -1,  # Unbounded
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any(f["severity"] == "HIGH" and "unbounded" in f["title"].lower() for f in findings)

    def test_large_message_size(self):
        """Test detection of large max message size (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "blobs",
                    "max_message_bytes": 5242880,  # 5MB
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any(f["severity"] == "HIGH" and "message" in f["title"].lower() for f in findings)

    def test_high_storage_multiplier(self):
        """Test detection of high storage multiplier (HIGH)."""
        data = {
            "topics": [
                {
                    "name": "heavy",
                    "replication_factor": 5,
                    "partitions": 10,  # 50 storage units
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        assert any(
            f["severity"] == "HIGH" and "storage multiplier" in f["title"].lower() for f in findings
        )

    def test_good_kafka_config(self):
        """Test that well-configured topic produces minimal findings."""
        data = {
            "topics": [
                {
                    "name": "production-safe",
                    "replication_factor": 3,
                    "partitions": 6,
                    "retention_ms": 604800000,
                    "retention_bytes": 1073741824,
                    "min_insync_replicas": 2,
                    "cleanup_policy": "delete",
                    "max_message_bytes": 1048576,
                }
            ]
        }
        findings = evaluate_kafka_config(data, "test.yaml")
        # May have some findings but should not have critical ones
        assert not any(f["severity"] == "CRITICAL" for f in findings)


class TestTerraformStaticAnalysis:
    """Test static Terraform infrastructure analysis."""

    def test_s3_weak_public_access_block(self):
        """Test detection of weak S3 public access block (CRITICAL)."""
        data = {
            "resource": [
                {
                    "aws_s3_bucket_public_access_block": {
                        "example": {
                            "block_public_acls": False,
                            "block_public_policy": True,
                            "ignore_public_acls": True,
                            "restrict_public_buckets": True,
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(
            f["severity"] == "CRITICAL" and "public access" in f["title"].lower() for f in findings
        )

    def test_s3_missing_encryption(self):
        """Test detection of missing S3 encryption (HIGH)."""
        data = {
            "resource": [
                {
                    "aws_s3_bucket": {
                        "config_bucket": {
                            "bucket": "my-config",
                            # Missing server_side_encryption_configuration
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(f["severity"] == "HIGH" and "encryption" in f["title"].lower() for f in findings)

    def test_s3_missing_versioning(self):
        """Test detection of missing S3 versioning (MEDIUM)."""
        data = {
            "resource": [
                {
                    "aws_s3_bucket": {
                        "data_bucket": {
                            "bucket": "my-data",
                            # Missing versioning
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(f["severity"] == "MEDIUM" and "version" in f["title"].lower() for f in findings)

    def test_iam_over_permissive(self):
        """Test detection of over-permissive IAM policy (HIGH)."""
        data = {
            "resource": [
                {
                    "aws_iam_policy": {
                        "admin": {
                            "policy": '"Action":"*"',
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(f["severity"] == "HIGH" for f in findings)

    def test_gcp_bucket_missing_uniform_access(self):
        """Test detection of GCP bucket without uniform access (HIGH)."""
        data = {
            "resource": [
                {
                    "google_storage_bucket": {
                        "logs": {
                            "name": "project-logs",
                            "location": "US",
                            # Missing uniform_bucket_level_access
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(f["severity"] == "HIGH" for f in findings)

    def test_azure_storage_public_blob_access(self):
        """Test detection of Azure storage with public blob access (CRITICAL)."""
        data = {
            "resource": [
                {
                    "azurerm_storage_account": {
                        "example": {
                            "name": "examplesa",
                            "allow_blob_public_access": True,  # CRITICAL
                        }
                    }
                }
            ]
        }
        findings = evaluate_terraform_config(data, "main.tf")
        assert any(f["severity"] == "CRITICAL" for f in findings)


class TestStaticScoringAndDecision:
    """Test production readiness scoring and decision logic."""

    def test_score_calculation_no_findings(self):
        """Test score with no findings."""
        findings = []
        score = calculate_score(findings)
        assert score == 100

    def test_score_calculation_with_critical(self):
        """Test score with critical findings."""
        findings = [finding("CRITICAL", "Critical issue", "High impact", "Fix now", "test.yaml")]
        score = calculate_score(findings)
        assert score < 85  # 100 - 20 = 80

    def test_score_calculation_with_multiple_findings(self):
        """Test score with mixed severity findings."""
        findings = [
            finding("CRITICAL", "Critical", "High", "Fix", "test1.yaml"),
            finding("HIGH", "High", "Medium", "Review", "test2.yaml"),
            finding("MEDIUM", "Medium", "Low", "Consider", "test3.yaml"),
        ]
        score = calculate_score(findings)
        # 100 - 20 - 12 - 7 = 61
        assert score == 61

    def test_score_minimum_floor(self):
        """Test that score never goes below 0."""
        findings = [finding("CRITICAL", "Issue", "Impact", "Fix", "test.yaml") for _ in range(10)]
        score = calculate_score(findings)
        assert score >= 0
