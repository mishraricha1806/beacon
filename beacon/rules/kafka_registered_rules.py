from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def replication_factor_low(resource, context):
    rf = resource.attributes.get("replication_factor")

    if rf is None or rf >= 3:
        return None

    return Finding(
        rule_id="kafka.topic.replication_factor.low",
        domain="kafka",
        category="resiliency",
        severity="CRITICAL",
        title=f"Kafka topic '{resource.name}' has replication factor {rf}",
        impact=(
            "A broker failure can make this topic unavailable and interrupt "
            "production workflows."
        ),
        recommendation="Use replication_factor=3 for production Kafka topics.",
        file=resource.source,
        evidence={
            "topic": resource.name,
            "replication_factor": rf,
            "expected_minimum": 3,
        },
        tags=["kafka", "availability", "production-readiness"],
    )


registry.register(
    Rule(
        rule_id="kafka.topic.replication_factor.low",
        domain="kafka",
        category="resiliency",
        severity="CRITICAL",
        title="Kafka topic replication factor too low",
        description=(
            "Detects Kafka topics with replication factor below production-safe "
            "threshold."
        ),
        supported_resource_types=["kafka_topic"],
        evaluator=replication_factor_low,
        tags=["kafka", "availability", "resiliency"],
    )
)
