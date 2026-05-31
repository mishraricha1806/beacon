from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_flow_finding(
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
        domain="flow",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def downstream_database_bottleneck(resource, context):
    signals = resource.attributes.get("signals", {})

    if not (
        signals.get("kafka_consumer_lag_increasing")
        and signals.get("db_latency_ms", 0) >= 500
        and not signals.get("kafka_broker_unhealthy", False)
    ):
        return None

    return build_flow_finding(
        resource,
        "flow.runtime.downstream_db_bottleneck",
        "runtime_stability",
        "HIGH",
        f"Flow '{resource.name}' likely has a downstream database bottleneck",
        "Kafka lag is increasing while Kafka appears healthy and database latency is elevated.",
        "Investigate database latency, connection pools, slow queries, retries, and consumer processing time before scaling Kafka.",
        {
            "flow": resource.name,
            "kafka_consumer_lag_increasing": signals.get(
                "kafka_consumer_lag_increasing"
            ),
            "kafka_broker_unhealthy": signals.get("kafka_broker_unhealthy", False),
            "db_latency_ms": signals.get("db_latency_ms"),
        },
        ["flow", "database", "root-cause"],
    )


def deployment_triggered_degradation(resource, context):
    signals = resource.attributes.get("signals", {})

    if not (
        signals.get("recent_deployment")
        and (
            signals.get("api_error_rate_percent", 0) >= 5
            or signals.get("latency_p95_ms", 0) >= 1000
            or signals.get("kafka_consumer_lag_increasing")
        )
    ):
        return None

    return build_flow_finding(
        resource,
        "flow.runtime.deployment_correlated_degradation",
        "runtime_stability",
        "HIGH",
        f"Flow '{resource.name}' degraded after a recent deployment",
        "Runtime degradation is correlated with a recent deployment signal.",
        "Review the deployment diff, rollout health, error budget impact, and rollback safety before scaling unrelated infrastructure.",
        {
            "flow": resource.name,
            "recent_deployment": signals.get("recent_deployment"),
            "api_error_rate_percent": signals.get("api_error_rate_percent"),
            "latency_p95_ms": signals.get("latency_p95_ms"),
            "kafka_consumer_lag_increasing": signals.get(
                "kafka_consumer_lag_increasing"
            ),
        },
        ["flow", "deployment", "correlation"],
    )


def cascading_latency(resource, context):
    signals = resource.attributes.get("signals", {})

    if not (
        signals.get("api_timeout_rate_percent", 0) >= 3
        and signals.get("consumer_retry_rate_percent", 0) >= 5
        and signals.get("kafka_consumer_lag_increasing")
    ):
        return None

    return build_flow_finding(
        resource,
        "flow.runtime.cascading_latency",
        "runtime_stability",
        "CRITICAL",
        f"Flow '{resource.name}' shows cascading latency",
        "API timeouts, consumer retries, and Kafka lag are increasing together, indicating a cascading runtime failure.",
        "Stabilize the highest-pressure downstream dependency, reduce retry amplification, and consider rollback or throttling before broad scaling.",
        {
            "flow": resource.name,
            "api_timeout_rate_percent": signals.get("api_timeout_rate_percent"),
            "consumer_retry_rate_percent": signals.get("consumer_retry_rate_percent"),
            "kafka_consumer_lag_increasing": signals.get(
                "kafka_consumer_lag_increasing"
            ),
        },
        ["flow", "cascade", "incident"],
    )


def component_unhealthy(resource, context):
    signals = resource.attributes.get("signals", {})

    if not signals.get("unhealthy"):
        return None

    component_type = resource.attributes.get("component_type", "component")

    return build_flow_finding(
        resource,
        "flow.runtime.component_unhealthy",
        "runtime_stability",
        "HIGH",
        f"Flow component '{resource.name}' is unhealthy",
        "An unhealthy component in a runtime flow can become the bottleneck or failure source for dependent services.",
        "Inspect this component first, then validate upstream retry behavior and downstream saturation.",
        {
            "flow": resource.attributes.get("flow"),
            "component": resource.name,
            "component_type": component_type,
            "signals": signals,
        },
        ["flow", "component", "health"],
    )


def register(
    rule_id,
    resource_type,
    category,
    severity,
    title,
    description,
    evaluator,
    tags,
):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="flow",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=[resource_type],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "flow.runtime.downstream_db_bottleneck",
    "flow_runtime",
    "runtime_stability",
    "HIGH",
    "Flow downstream database bottleneck",
    "Detects Kafka lag patterns that are more likely caused by downstream database latency than Kafka broker failure.",
    downstream_database_bottleneck,
    ["flow", "database", "root-cause"],
)

register(
    "flow.runtime.deployment_correlated_degradation",
    "flow_runtime",
    "runtime_stability",
    "HIGH",
    "Flow deployment-correlated degradation",
    "Detects runtime degradation correlated with recent deployment signals.",
    deployment_triggered_degradation,
    ["flow", "deployment", "correlation"],
)

register(
    "flow.runtime.cascading_latency",
    "flow_runtime",
    "runtime_stability",
    "CRITICAL",
    "Flow cascading latency",
    "Detects cascading runtime failure across API timeouts, retries, and Kafka lag.",
    cascading_latency,
    ["flow", "cascade", "incident"],
)

register(
    "flow.runtime.component_unhealthy",
    "flow_component_runtime",
    "runtime_stability",
    "HIGH",
    "Flow component unhealthy",
    "Detects unhealthy components inside a runtime flow snapshot.",
    component_unhealthy,
    ["flow", "component", "health"],
)
