import json
from datetime import datetime

import yaml

from beacon.kafka_runtime_connector import finding


def analyze_kafka_history_file(path):
    with open(path, "r") as f:
        if path.endswith(".json"):
            data = json.load(f) or {}
        else:
            data = yaml.safe_load(f) or {}

    return analyze_kafka_history(data, source=path)


def analyze_kafka_history(data, source="kafka-history"):
    snapshots = normalize_history(data)

    if len(snapshots) < 2:
        return [
            finding(
                "LOW",
                "Kafka history has insufficient snapshots",
                "Beacon needs at least two Kafka runtime snapshots to detect trends.",
                "Collect multiple snapshots over time or upload a history export.",
                rule_id="kafka.history.insufficient_snapshots",
                evidence={"snapshot_count": len(snapshots), "source": source},
                confidence="HIGH",
            )
        ]

    findings = []
    ordered = sorted(snapshots, key=snapshot_time_key)
    first = ordered[0]
    last = ordered[-1]

    findings.extend(check_numeric_growth(first, last, source))
    findings.extend(check_workload_and_deployment_trends(first, last, ordered, source))
    findings.extend(check_counter_accumulation(ordered, source))
    findings.extend(check_member_churn(ordered, source))

    if not findings:
        findings.append(
            finding(
                "LOW",
                "Kafka history trend inspected",
                "Beacon inspected Kafka runtime history and did not detect worsening disk, lag, controller, rebalance, or membership trends.",
                "Continue collecting snapshots before and during high-traffic events.",
                rule_id="kafka.history.trend.inspected",
                evidence={"snapshot_count": len(ordered), "source": source},
                confidence="HIGH",
            )
        )

    return findings


def check_workload_and_deployment_trends(first, last, snapshots, source):
    findings = []
    first_rate = numeric(first.get("producer_rate_messages_per_sec"))
    latest_rate = numeric(last.get("producer_rate_messages_per_sec"))
    first_lag = numeric(first.get("total_consumer_lag"))
    latest_lag = numeric(last.get("total_consumer_lag"))

    if first_rate is not None and latest_rate is not None:
        delta = latest_rate - first_rate
        growth_percent = percent_growth(first_rate, latest_rate)
        if delta >= 1000 or growth_percent >= 50:
            findings.append(
                finding(
                    "HIGH",
                    "Kafka producer rate increased across history",
                    "Producer throughput increased significantly across the sampled window and may be contributing to lag, broker pressure, or storage growth.",
                    "Validate whether the producer rate change was expected. Compare producer deployments, payload changes, consumer drain rate, and broker capacity.",
                    rule_id="kafka.history.producer_rate.increased",
                    evidence={
                        "first_producer_rate_messages_per_sec": first_rate,
                        "latest_producer_rate_messages_per_sec": latest_rate,
                        "delta_messages_per_sec": delta,
                        "growth_percent": growth_percent,
                        "source": source,
                    },
                    confidence="HIGH",
                )
            )

    if recent_deployment_seen(snapshots) and first_lag is not None and latest_lag:
        lag_delta = latest_lag - first_lag
        if lag_delta >= 50000 and latest_lag >= 100000:
            findings.append(
                finding(
                    "HIGH",
                    "Kafka lag growth is correlated with deployment history",
                    "Consumer lag increased after or during a window with recent deployment signals.",
                    "Review producer and consumer deployment diffs, rollout timing, feature flags, retry behavior, and downstream dependency changes before scaling Kafka.",
                    rule_id="kafka.history.deployment_correlated_lag",
                    evidence={
                        "first_total_consumer_lag": first_lag,
                        "latest_total_consumer_lag": latest_lag,
                        "lag_delta": lag_delta,
                        "deployment_seen": True,
                        "source": source,
                    },
                    confidence="MEDIUM",
                )
            )

    return findings


def normalize_history(data):
    if isinstance(data, list):
        return data

    for key in ("kafka_history", "snapshots", "history"):
        if isinstance(data.get(key), list):
            return data[key]

    return []


def snapshot_time_key(snapshot):
    value = snapshot.get("timestamp") or snapshot.get("time") or ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def check_numeric_growth(first, last, source):
    checks = [
        (
            "broker_disk_usage_percent",
            10,
            80,
            "kafka.history.disk_usage.growing",
            "Kafka broker disk usage is increasing across history",
            "Disk usage is trending upward and the latest snapshot is already near or above warning levels.",
            "Review retention, producer volume, topic growth, broker skew, and capacity runway.",
        ),
        (
            "total_consumer_lag",
            50000,
            100000,
            "kafka.history.consumer_lag.growing",
            "Kafka consumer lag is increasing across history",
            "Consumer lag is growing over time, which indicates consumers are not keeping up with producer throughput.",
            "Investigate consumer processing latency, downstream dependencies, retry loops, hot partitions, and recent deployments.",
        ),
    ]
    findings = []

    for (
        field,
        min_delta,
        latest_threshold,
        rule_id,
        title,
        impact,
        recommendation,
    ) in checks:
        start = numeric(first.get(field))
        end = numeric(last.get(field))
        if start is None or end is None:
            continue

        delta = end - start
        if delta >= min_delta and end >= latest_threshold:
            findings.append(
                finding(
                    "HIGH",
                    title,
                    impact,
                    recommendation,
                    rule_id=rule_id,
                    evidence={
                        "field": field,
                        "first": start,
                        "latest": end,
                        "delta": delta,
                        "source": source,
                    },
                    confidence="HIGH",
                )
            )

    return findings


def check_counter_accumulation(snapshots, source):
    latest = snapshots[-1]
    findings = []

    if (
        numeric(latest.get("controller_change_count_15m"))
        and numeric(latest.get("controller_change_count_15m")) >= 3
    ):
        findings.append(
            finding(
                "HIGH",
                "Kafka controller churn is high in recent history",
                "Frequent controller changes can indicate broker instability, quorum issues, network disruption, or overloaded controllers.",
                "Inspect controller logs, broker churn, quorum health, GC pauses, and network instability.",
                rule_id="kafka.history.controller_churn.high",
                evidence={
                    "controller_change_count_15m": latest.get("controller_change_count_15m"),
                    "source": source,
                },
                confidence="HIGH",
            )
        )

    if (
        numeric(latest.get("rebalance_count_15m"))
        and numeric(latest.get("rebalance_count_15m")) >= 3
    ):
        findings.append(
            finding(
                "HIGH",
                "Kafka rebalance churn is high in recent history",
                "Frequent rebalances can pause consumption and amplify lag during incidents.",
                "Inspect deployments, heartbeat/session timeout, max.poll.interval.ms, and consumer crashes.",
                rule_id="kafka.history.rebalance_churn.high",
                evidence={
                    "rebalance_count_15m": latest.get("rebalance_count_15m"),
                    "source": source,
                },
                confidence="HIGH",
            )
        )

    return findings


def check_member_churn(snapshots, source):
    groups = {}

    for snapshot in snapshots:
        for group in snapshot.get("consumer_groups", []) or []:
            group_id = group.get("group_id") or group.get("name")
            if not group_id:
                continue
            members = tuple(sorted(str(member) for member in group.get("members", [])))
            groups.setdefault(group_id, set()).add(members)

    findings = []

    for group_id, member_sets in groups.items():
        if len(member_sets) >= 3:
            findings.append(
                finding(
                    "HIGH",
                    f"Kafka consumer group '{group_id}' has historical member churn",
                    "Consumer membership changed repeatedly across history snapshots, which can cause rebalance storms and lag spikes.",
                    "Inspect rolling deployments, pod restarts, session timeout, heartbeat interval, max.poll.interval.ms, and consumer crashes.",
                    rule_id="kafka.history.consumer_group.member_churn",
                    evidence={
                        "consumer_group": group_id,
                        "unique_member_set_count": len(member_sets),
                        "source": source,
                    },
                    confidence="HIGH",
                )
            )

    return findings


def numeric(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percent_growth(first, latest):
    if first is None or latest is None:
        return None
    if first <= 0:
        return 100 if latest > 0 else 0
    return round(((latest - first) / first) * 100, 2)


def recent_deployment_seen(snapshots):
    for snapshot in snapshots:
        if snapshot.get("recent_deployment") or snapshot.get("deployment_recent"):
            return True
        deployments = snapshot.get("deployments", []) or []
        if any(deployment.get("recent") or deployment.get("changed") for deployment in deployments):
            return True
    return False
