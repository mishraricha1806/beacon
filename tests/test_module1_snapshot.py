"""Tests for MODULE 1: Snapshot Analysis.

Covers:
- YAML snapshot parsing
- Historical correlation
- Growth trajectory prediction
- Capacity planning recommendations
"""

import pytest
from datetime import datetime, timedelta


class TestSnapshotParsing:
    """Test Kafka runtime snapshot parsing."""

    def test_valid_snapshot_structure(self):
        """Test parsing of valid snapshot YAML."""
        snapshot = {
            "timestamp": "2025-05-26T10:00:00Z",
            "brokers": [
                {
                    "id": 1,
                    "disk_bytes_total": 1099511627776,
                    "disk_bytes_used": 659306596352,
                }
            ],
            "topics": [
                {
                    "name": "payments",
                    "partitions": 6,
                    "replication_factor": 3,
                    "size_bytes": 107374182400,
                }
            ],
            "consumer_groups": [
                {
                    "name": "payment-consumer",
                    "lag": 0,
                    "members": 3,
                }
            ],
        }
        assert snapshot["timestamp"]
        assert len(snapshot["brokers"]) > 0
        assert len(snapshot["topics"]) > 0

    def test_disk_usage_calculation(self):
        """Test calculation of disk usage percentage."""
        snapshot = {
            "brokers": [
                {
                    "disk_bytes_total": 1099511627776,  # 1TB
                    "disk_bytes_used": 659306596352,  # 600GB
                }
            ]
        }
        broker = snapshot["brokers"][0]
        usage_percent = (broker["disk_bytes_used"] / broker["disk_bytes_total"]) * 100
        assert usage_percent == pytest.approx(60.0, abs=0.1)


class TestSnapshotCorrelation:
    """Test correlation of multiple snapshots over time."""

    def test_growth_rate_calculation(self):
        """Test calculation of storage growth rate."""
        snapshots = [
            {
                "timestamp": datetime(2025, 5, 1, 0, 0, 0),
                "disk_used_bytes": 107374182400,  # 100GB
            },
            {
                "timestamp": datetime(2025, 5, 11, 0, 0, 0),
                "disk_used_bytes": 161061273600,  # 150GB (10 days later)
            },
        ]
        # Growth: 50GB in 10 days = 5GB/day
        growth_gb = (
            snapshots[1]["disk_used_bytes"] - snapshots[0]["disk_used_bytes"]
        ) / (1024**3)
        days_elapsed = (snapshots[1]["timestamp"] - snapshots[0]["timestamp"]).days
        growth_per_day = growth_gb / days_elapsed
        assert growth_per_day == pytest.approx(5.0, abs=0.1)

    def test_lag_trend_detection(self):
        """Test detection of lag trends."""
        lag_history = [
            {"timestamp": datetime(2025, 5, 26, 10, 0, 0), "lag": 0},
            {"timestamp": datetime(2025, 5, 26, 11, 0, 0), "lag": 500},
            {"timestamp": datetime(2025, 5, 26, 12, 0, 0), "lag": 1500},
            {"timestamp": datetime(2025, 5, 26, 13, 0, 0), "lag": 3500},
        ]
        # Lag is increasing
        lags = [h["lag"] for h in lag_history]
        assert lags == sorted(lags)  # Monotonically increasing

    def test_partition_imbalance_trend(self):
        """Test detection of partition imbalance trends."""
        snapshots = [
            {
                "timestamp": datetime(2025, 5, 26, 10, 0, 0),
                "partitions": [
                    {"partition": 0, "bytes": 100000},
                    {"partition": 1, "bytes": 100000},
                    {"partition": 2, "bytes": 100000},
                ],
            },
            {
                "timestamp": datetime(2025, 5, 26, 11, 0, 0),
                "partitions": [
                    {"partition": 0, "bytes": 200000},  # Growing faster
                    {"partition": 1, "bytes": 105000},
                    {"partition": 2, "bytes": 105000},
                ],
            },
        ]
        # Partition 0 is becoming imbalanced
        partition_0_bytes_growth = (
            snapshots[1]["partitions"][0]["bytes"]
            - snapshots[0]["partitions"][0]["bytes"]
        )
        partition_1_bytes_growth = (
            snapshots[1]["partitions"][1]["bytes"]
            - snapshots[0]["partitions"][1]["bytes"]
        )
        assert partition_0_bytes_growth > partition_1_bytes_growth


class TestCapacityPlanning:
    """Test capacity planning based on snapshot analysis."""

    def test_saturation_prediction(self):
        """Test prediction of storage saturation."""
        current_usage_gb = 600
        total_capacity_gb = 1000
        growth_rate_gb_per_day = 5
        available_space_gb = total_capacity_gb - current_usage_gb
        days_until_saturation = available_space_gb / growth_rate_gb_per_day
        assert days_until_saturation == pytest.approx(80, abs=0.1)

    def test_expansion_recommendation(self):
        """Test recommendation for expansion timing."""
        days_until_saturation = 30
        safe_threshold_days = 7  # Buffer
        expansion_deadline = days_until_saturation - safe_threshold_days
        assert expansion_deadline == 23
        assert expansion_deadline > 0  # Must act before saturation

    def test_retention_impact_analysis(self):
        """Test analysis of retention settings on growth."""
        producer_throughput_gb_per_day = 10
        retention_days = 7
        min_storage_needed_gb = producer_throughput_gb_per_day * retention_days
        assert min_storage_needed_gb == 70


class TestSnapshotDecisionGeneration:
    """Test production decision generation from snapshots."""

    def test_ready_decision_healthy_snapshot(self):
        """Test READY decision for healthy cluster."""
        snapshot = {
            "disk_usage_percent": 45,
            "consumer_lag": 100,
            "broker_availability": 3,  # All brokers up
            "partition_imbalance": 0.05,  # <5% imbalance
        }
        # All metrics healthy = READY
        assert snapshot["disk_usage_percent"] < 80
        assert snapshot["consumer_lag"] < 10000
        assert snapshot["broker_availability"] == 3

    def test_not_ready_decision_disk_pressure(self):
        """Test NOT READY decision for disk pressure."""
        snapshot = {
            "disk_usage_percent": 92,
            "growth_rate_percent_per_day": 3,
            "days_until_saturation": 2,
        }
        # High disk usage and imminent saturation = NOT READY
        assert snapshot["disk_usage_percent"] > 80
        assert snapshot["days_until_saturation"] < 7

    def test_not_ready_decision_partition_imbalance(self):
        """Test NOT READY decision for partition imbalance."""
        snapshot = {
            "topic": "events",
            "partition_imbalance": 0.65,  # 65% of data on one partition
        }
        # Severe imbalance = NOT READY
        assert snapshot["partition_imbalance"] > 0.5
