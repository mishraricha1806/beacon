from beacon.engine.models import Finding
from beacon.engine.registry import registry


def evaluate(resources, context=None):
    context = context or {}
    findings = []

    for resource in resources:
        rules = registry.get_for_resource(resource)

        for rule in rules:
            try:
                result = rule.evaluator(resource, context)

                if not result:
                    continue

                if isinstance(result, list):
                    findings.extend(to_dict(item) for item in result)
                else:
                    findings.append(to_dict(result))

            except Exception as error:
                findings.append(
                    Finding(
                        rule_id="engine.rule.execution_failed",
                        domain="engine",
                        category="operational_safety",
                        severity="ERROR",
                        title=f"Rule execution failed: {rule.rule_id}",
                        impact=str(error),
                        recommendation=(
                            "Review rule implementation and normalized resource input."
                        ),
                        file=context.get("file", resource.source),
                        evidence={
                            "resource": resource.name,
                            "resource_type": resource.type,
                            "rule_id": rule.rule_id,
                            "error": str(error),
                        },
                        tags=["engine", "rule-execution"],
                    ).to_dict()
                )

    return findings


def to_dict(finding):
    if hasattr(finding, "to_dict"):
        return finding.to_dict()

    return finding


def evaluate_resource(resource, context=None):
    return evaluate([resource], context=context)
