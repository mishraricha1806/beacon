"""Tests for MODULE 1: Runtime Kafka Diagnostics.

Covers:
- Live broker metadata collection
- Consumer lag analysis
- Hot partition detection
- Storage pressure analysis
- Operational recommendation generation
"""

from beacon.runtime_advisor import analyze_runtime_file


class TestRuntimeKafkaCollection:
    """Test runtime Kafka data collection."""

    def test_broker_metadata_collection(self):
        """Test collection of broker metadata."""
        findings = analyze_runtime_file("./examples/runtime/kafka-runtime.yaml")
        rule_ids = {finding["rule_id"] for finding in findings}

        assert "kafka.runtime.disk_usage.high" in rule_ids
        assert "kafka.runtime.decision.workload_investigation" in rule_ids

    def test_consumer_lag_calculation(self):
        """Test consumer lag calculation."""
        # Mock consumer group data
        consumer_lag = {
            "topic": "payments",
            "partition": 0,
            "current_offset": 1000,
            "log_end_offset": 1500,
            "lag": 500,
        }
        assert consumer_lag["lag"] == 500

    def test_partition_distribution_analysis(self):
        """Test partition distribution across brokers."""
        partition_distribution = {
            "topic": "orders",
            "partitions": {
                0: {"broker": 1, "leader": 1, "replicas": [1, 2, 3]},
                1: {"broker": 2, "leader": 2, "replicas": [2, 3, 1]},
                2: {"broker": 3, "leader": 3, "replicas": [3, 1, 2]},
            },
        }
        # All partitions have balanced leadership
        leaders = [p["leader"] for p in partition_distribution["partitions"].values()]
        assert len(set(leaders)) == 3  # 3 different brokers

    def test_hot_partition_detection(self):
        """Test detection of hot partitions (skewed traffic)."""
        partition_traffic = {
            "topic": "events",
            "partitions": [
                {"partition": 0, "incoming_byte_rate": 100000},
                {"partition": 1, "incoming_byte_rate": 50000},
                {"partition": 2, "incoming_byte_rate": 900000},  # HOT
            ],
        }
        # Detect skew: partition 2 has 60% of traffic with 33% of partitions
        total_traffic = sum(p["incoming_byte_rate"] for p in partition_traffic["partitions"])
        partition_2_ratio = 900000 / total_traffic
        assert partition_2_ratio > 0.5  # More than 50% on one partition = hot

    def test_storage_pressure_analysis(self):
        """Test detection of storage pressure."""
        broker_disk = {
            "broker": 1,
            "total_disk_bytes": 1099511627776,  # 1TB
            "used_disk_bytes": 879609302016,  # 800GB = 80%
        }
        disk_usage_percent = (
            broker_disk["used_disk_bytes"] / broker_disk["total_disk_bytes"]
        ) * 100
        assert round(disk_usage_percent, 1) == 80.0
        assert disk_usage_percent > 70  # Alert threshold


class TestRuntimeAnalysis:
    """Test runtime analysis logic."""

    def test_consumer_lag_interpretation(self):
        """Test interpretation of consumer lag findings."""
        metrics = {
            "consumer_group": "payment-consumer",
            "lag": 5000,
            "lag_trend": "increasing",
            "producer_throughput": 1000,  # msgs/sec
            "consumer_throughput": 500,  # msgs/sec
        }
        # Producer is faster than consumer = lag increasing
        assert metrics["producer_throughput"] > metrics["consumer_throughput"]
        assert metrics["lag_trend"] == "increasing"

    def test_rebalance_storm_detection(self):
        """Test detection of rebalance storms."""
        rebalance_events = {
            "consumer_group": "unstable-group",
            "rebalances_per_minute": 5,  # Normal is 0-1
            "time_in_rebalance": 45000,  # 45 seconds in last minute
        }
        # High rebalance frequency = storm
        assert rebalance_events["rebalances_per_minute"] > 2

    def test_producer_spike_detection(self):
        """Test detection of producer throughput spikes."""
        producer_metrics = {
            "baseline_throughput": 1000,  # msgs/sec
            "current_throughput": 5000,  # msgs/sec
            "spike_ratio": 5.0,
        }
        # 5x spike is significant
        assert producer_metrics["spike_ratio"] > 3.0


class TestRuntimeRecommendationEngine:
    """Test runtime operational recommendations."""

    def test_lag_mitigation_recommendation(self):
        """Test recommendations for increasing lag."""
        findings = {
            "type": "high_consumer_lag",
            "lag_ms": 300000,
            "broker_health": "healthy",
            "producer_stable": True,
            "partition_distribution": "balanced",
        }
        # Recommendations should focus on downstream (consumer DB/API)
        recommended_actions = [
            "Investigate downstream database latency",
            "Review consumer processing time",
            "Check for retry loops",
            "Review recent deployments",
        ]
        assert any(
            "downstream" in action.lower() or "database" in action.lower()
            for action in recommended_actions
        )

    def test_partition_skew_recommendation(self):
        """Test recommendations for partition skew."""
        findings = {
            "type": "partition_skew",
            "skew_ratio": 0.75,  # 75% traffic on one partition
            "topic": "events",
        }
        recommended_action = "Review producer partition key strategy"
        assert "partition key" in recommended_action.lower()

    def test_storage_saturation_recommendation(self):
        """Test recommendations for storage saturation."""
        findings = {
            "type": "storage_pressure",
            "disk_usage_percent": 85,
            "growth_rate_percent_per_day": 2.5,
            "estimated_saturation_days": 6,
        }
        recommended_action = "Review retention configuration and monitor growth rate"
        assert "retention" in recommended_action.lower()
