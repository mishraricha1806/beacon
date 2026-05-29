from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_database_finding(resource, rule_id, category, severity, title, impact, recommendation, evidence, tags=None):
    return Finding(
        rule_id=rule_id,
        domain="database",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def high_latency(resource, context):
    latency = resource.attributes.get("latency_ms")

    if latency is None or latency < 500:
        return None

    return build_database_finding(
        resource,
        "database.runtime.latency.high",
        "runtime_stability",
        "HIGH",
        f"Database '{resource.name}' has high latency",
        "High database latency can slow consumers, APIs, and background jobs.",
        "Inspect slow queries, indexes, connection pool pressure, locks, and recent workload changes.",
        {"database": resource.name, "engine": resource.attributes.get("engine"), "latency_ms": latency},
        ["database", "latency"],
    )


def connection_pool_exhaustion(resource, context):
    utilization = resource.attributes.get("connection_pool_utilization_percent")

    if utilization is None or utilization < 85:
        return None

    severity = "CRITICAL" if utilization >= 95 else "HIGH"

    return build_database_finding(
        resource,
        "database.runtime.connection_pool.exhaustion",
        "scalability",
        severity,
        f"Database '{resource.name}' connection pool is near exhaustion",
        "Connection pool exhaustion can block API and consumer progress even when the database host is healthy.",
        "Tune pool limits, reduce connection leaks, review query time, and add backpressure before only scaling app replicas.",
        {"database": resource.name, "connection_pool_utilization_percent": utilization},
        ["database", "connections", "capacity"],
    )


def replication_lag_high(resource, context):
    lag = resource.attributes.get("replication_lag_seconds")

    if lag is None or lag < 60:
        return None

    return build_database_finding(
        resource,
        "database.runtime.replication_lag.high",
        "recovery_readiness",
        "HIGH",
        f"Database '{resource.name}' replication lag is high",
        "High replication lag can weaken failover safety and produce stale reads.",
        "Investigate replica throughput, write spikes, network health, long transactions, and failover readiness.",
        {"database": resource.name, "replication_lag_seconds": lag},
        ["database", "replication", "failover"],
    )


def lock_contention(resource, context):
    if not resource.attributes.get("lock_waits_high"):
        return None

    return build_database_finding(
        resource,
        "database.runtime.lock_contention.high",
        "runtime_stability",
        "HIGH",
        f"Database '{resource.name}' has high lock contention",
        "Lock contention can increase latency and stall application progress.",
        "Identify blocking sessions, long transactions, migration activity, and hot rows or tables.",
        {"database": resource.name, "lock_waits_high": True},
        ["database", "locks"],
    )


def storage_saturation(resource, context):
    used = resource.attributes.get("storage_used_percent")

    if used is None or used < 85:
        return None

    severity = "CRITICAL" if used >= 95 else "HIGH"

    return build_database_finding(
        resource,
        "database.runtime.storage_saturation",
        "storage_sustainability",
        severity,
        f"Database '{resource.name}' storage usage is high",
        "Database storage saturation can cause write failures, replication instability, and recovery risk.",
        "Create storage headroom, review growth drivers, retention, indexing, and backup/restore timelines.",
        {"database": resource.name, "storage_used_percent": used},
        ["database", "storage", "capacity"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="database",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["database_runtime_instance"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register("database.runtime.latency.high", "runtime_stability", "HIGH", "Database latency high", "Detects databases with high runtime latency.", high_latency, ["database", "latency"])
register("database.runtime.connection_pool.exhaustion", "scalability", "HIGH", "Database connection pool exhaustion", "Detects near-exhausted database connection pools.", connection_pool_exhaustion, ["database", "connections"])
register("database.runtime.replication_lag.high", "recovery_readiness", "HIGH", "Database replication lag high", "Detects unsafe database replication lag.", replication_lag_high, ["database", "replication"])
register("database.runtime.lock_contention.high", "runtime_stability", "HIGH", "Database lock contention high", "Detects high lock contention.", lock_contention, ["database", "locks"])
register("database.runtime.storage_saturation", "storage_sustainability", "HIGH", "Database storage saturation", "Detects high database storage utilization.", storage_saturation, ["database", "storage"])
