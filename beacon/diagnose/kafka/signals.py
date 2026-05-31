from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KafkaRuntimeSignal:
    broker_disk_usage_percent: Optional[float] = None
    broker_disk_usage_by_broker: Optional[Dict[str, float]] = None
    disk_growth_percent_7d: Optional[float] = None
    retention_bytes_configured: Optional[bool] = None
    cleanup_policy_configured: Optional[bool] = None
    producer_rate_increased: Optional[bool] = None
    producer_error_rate_percent: Optional[float] = None
    consumer_lag_increasing: Optional[bool] = None
    consumer_group_state: Optional[str] = None
    active_members: Optional[int] = None
    expected_members: Optional[int] = None
    rebalance_count_15m: Optional[int] = None
    avg_message_size_increased: Optional[bool] = None
    under_replicated_partitions: Optional[int] = None
    under_min_isr_partitions: Optional[int] = None
    offline_partitions: Optional[int] = None
    leader_imbalance_percent: Optional[float] = None
    request_latency_p95_ms: Optional[float] = None
    network_io_utilization_percent: Optional[float] = None
    broker_count: Optional[int] = None
    partition_count: Optional[int] = None
    replication_factor: Optional[int] = None

    @classmethod
    def from_snapshot(cls, runtime: Dict[str, Any]):
        return cls(
            broker_disk_usage_percent=runtime.get("broker_disk_usage_percent"),
            broker_disk_usage_by_broker=runtime.get("broker_disk_usage_by_broker"),
            disk_growth_percent_7d=runtime.get("disk_growth_percent_7d"),
            retention_bytes_configured=runtime.get("retention_bytes_configured"),
            cleanup_policy_configured=runtime.get("cleanup_policy_configured"),
            producer_rate_increased=runtime.get("producer_rate_increased"),
            producer_error_rate_percent=runtime.get("producer_error_rate_percent"),
            consumer_lag_increasing=runtime.get("consumer_lag_increasing"),
            consumer_group_state=runtime.get("consumer_group_state"),
            active_members=runtime.get("active_members"),
            expected_members=runtime.get("expected_members"),
            rebalance_count_15m=runtime.get("rebalance_count_15m"),
            avg_message_size_increased=runtime.get("avg_message_size_increased"),
            under_replicated_partitions=runtime.get("under_replicated_partitions"),
            under_min_isr_partitions=runtime.get("under_min_isr_partitions"),
            offline_partitions=runtime.get("offline_partitions"),
            leader_imbalance_percent=runtime.get("leader_imbalance_percent"),
            request_latency_p95_ms=runtime.get("request_latency_p95_ms"),
            network_io_utilization_percent=runtime.get(
                "network_io_utilization_percent"
            ),
            broker_count=runtime.get("broker_count"),
            partition_count=runtime.get("partition_count"),
            replication_factor=runtime.get("replication_factor"),
        )

    def evidence(self):
        return {
            key: value
            for key, value in {
                "broker_disk_usage_percent": self.broker_disk_usage_percent,
                "broker_disk_usage_by_broker": self.broker_disk_usage_by_broker,
                "disk_growth_percent_7d": self.disk_growth_percent_7d,
                "retention_bytes_configured": self.retention_bytes_configured,
                "cleanup_policy_configured": self.cleanup_policy_configured,
                "producer_rate_increased": self.producer_rate_increased,
                "producer_error_rate_percent": self.producer_error_rate_percent,
                "consumer_lag_increasing": self.consumer_lag_increasing,
                "consumer_group_state": self.consumer_group_state,
                "active_members": self.active_members,
                "expected_members": self.expected_members,
                "rebalance_count_15m": self.rebalance_count_15m,
                "avg_message_size_increased": self.avg_message_size_increased,
                "under_replicated_partitions": self.under_replicated_partitions,
                "under_min_isr_partitions": self.under_min_isr_partitions,
                "offline_partitions": self.offline_partitions,
                "leader_imbalance_percent": self.leader_imbalance_percent,
                "request_latency_p95_ms": self.request_latency_p95_ms,
                "network_io_utilization_percent": self.network_io_utilization_percent,
                "broker_count": self.broker_count,
                "partition_count": self.partition_count,
                "replication_factor": self.replication_factor,
            }.items()
            if value is not None
        }

    @property
    def has_weak_storage_guardrails(self):
        return (
            self.retention_bytes_configured is False
            or self.cleanup_policy_configured is False
        )

    @property
    def has_workload_change(self):
        return bool(
            self.producer_rate_increased
            or self.avg_message_size_increased
            or self.consumer_lag_increasing
        )
