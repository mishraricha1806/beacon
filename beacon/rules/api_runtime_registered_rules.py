from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_api_finding(resource, rule_id, severity, title, impact, recommendation, evidence, tags=None):
    return Finding(
        rule_id=rule_id,
        domain="api",
        category="runtime_stability",
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def high_latency(resource, context):
    latency = resource.attributes.get("latency_p95_ms")

    if latency is None or latency < 1000:
        return None

    return build_api_finding(
        resource,
        "api.runtime.latency_p95.high",
        "HIGH",
        f"API service '{resource.name}' has high p95 latency",
        "High API latency can trigger client timeouts, retries, and downstream pressure.",
        "Review recent deployments, downstream dependency latency, saturation, and timeout budgets.",
        {"service": resource.name, "latency_p95_ms": latency},
        ["api", "latency"],
    )


def high_error_rate(resource, context):
    error_rate = resource.attributes.get("error_rate_percent")

    if error_rate is None or error_rate < 5:
        return None

    return build_api_finding(
        resource,
        "api.runtime.error_rate.high",
        "HIGH",
        f"API service '{resource.name}' has high error rate",
        "Elevated API errors can indicate runtime regression, dependency failure, or capacity exhaustion.",
        "Check error classes, recent deployment changes, dependency health, and rollback safety.",
        {"service": resource.name, "error_rate_percent": error_rate},
        ["api", "errors"],
    )


def high_timeout_rate(resource, context):
    timeout_rate = resource.attributes.get("timeout_rate_percent")

    if timeout_rate is None or timeout_rate < 3:
        return None

    return build_api_finding(
        resource,
        "api.runtime.timeout_rate.high",
        "HIGH",
        f"API service '{resource.name}' has high timeout rate",
        "Timeouts can amplify retries and create cascading load across dependencies.",
        "Review timeout budgets, dependency latency, queueing, and retry policy before scaling broadly.",
        {"service": resource.name, "timeout_rate_percent": timeout_rate},
        ["api", "timeouts"],
    )


def retry_amplification(resource, context):
    retry_rate = resource.attributes.get("retry_rate_percent")
    timeout_rate = resource.attributes.get("timeout_rate_percent") or 0
    error_rate = resource.attributes.get("error_rate_percent") or 0

    if retry_rate is None or retry_rate < 10 or (timeout_rate < 3 and error_rate < 5):
        return None

    return build_api_finding(
        resource,
        "api.runtime.retry_amplification",
        "CRITICAL",
        f"API service '{resource.name}' shows retry amplification",
        "High retries during errors or timeouts can intensify cascading degradation.",
        "Reduce retry aggressiveness, add backoff/jitter, protect downstream dependencies, and consider throttling.",
        {
            "service": resource.name,
            "retry_rate_percent": retry_rate,
            "timeout_rate_percent": timeout_rate,
            "error_rate_percent": error_rate,
        },
        ["api", "retries", "cascade"],
    )


def deployment_correlated_api_degradation(resource, context):
    if not resource.attributes.get("recent_deployment"):
        return None

    latency = resource.attributes.get("latency_p95_ms") or 0
    error_rate = resource.attributes.get("error_rate_percent") or 0

    if latency < 1000 and error_rate < 5:
        return None

    return build_api_finding(
        resource,
        "api.runtime.deployment_correlated_degradation",
        "HIGH",
        f"API service '{resource.name}' degraded after deployment",
        "API degradation is correlated with a recent deployment signal.",
        "Inspect the deployment diff, rollout health, feature flags, and rollback options.",
        {
            "service": resource.name,
            "recent_deployment": True,
            "latency_p95_ms": latency,
            "error_rate_percent": error_rate,
        },
        ["api", "deployment"],
    )


def register(rule_id, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="api",
            category="runtime_stability",
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["api_runtime_service"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register("api.runtime.latency_p95.high", "HIGH", "API p95 latency high", "Detects API services with high p95 latency.", high_latency, ["api", "latency"])
register("api.runtime.error_rate.high", "HIGH", "API error rate high", "Detects API services with elevated error rate.", high_error_rate, ["api", "errors"])
register("api.runtime.timeout_rate.high", "HIGH", "API timeout rate high", "Detects API services with elevated timeout rate.", high_timeout_rate, ["api", "timeouts"])
register("api.runtime.retry_amplification", "CRITICAL", "API retry amplification", "Detects retry amplification during API degradation.", retry_amplification, ["api", "retries", "cascade"])
register("api.runtime.deployment_correlated_degradation", "HIGH", "API deployment-correlated degradation", "Detects API degradation correlated with a recent deployment.", deployment_correlated_api_degradation, ["api", "deployment"])
