from beacon.engine.registry import get_rules


def evaluate_resource(resource, context=None):
    findings = []

    resource_type = resource.get("type")

    for rule in get_rules():

        if not rule.enabled:
            continue

        if resource_type not in rule.supported_types:
            continue

        try:
            result = rule.evaluator(resource, context)

            if not result:
                continue

            if isinstance(result, list):
                findings.extend(result)
            else:
                findings.append(result)

        except Exception as error:
            findings.append(
                {
                    "rule_id": "engine.rule.execution_failed",
                    "domain": "engine",
                    "category": "operational_safety",
                    "severity": "ERROR",
                    "title": (
                        f"Rule execution failed: {rule.rule_id}"
                    ),
                    "impact": str(error),
                    "recommendation": (
                        "Review rule evaluator implementation."
                    ),
                    "file": (
                        context.get("file")
                        if context
                        else "unknown"
                    ),
                    "evidence": {
                        "rule_id": rule.rule_id,
                        "error": str(error),
                    },
                    "tags": [
                        "engine",
                        "rule-execution",
                    ],
                }
            )

    return findings