from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def is_sha_pinned_action(reference):
    if not isinstance(reference, str) or "@" not in reference:
        return False

    _, ref = reference.rsplit("@", 1)
    return len(ref) == 40 and all(character in "0123456789abcdefABCDEF" for character in ref)


def is_external_action(reference):
    if not isinstance(reference, str):
        return False

    return not reference.startswith(("./", "docker://"))


def build_cicd_finding(
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
        domain="cicd",
        category=category,
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def deployment_job_missing_environment(resource, context):
    if not resource.attributes.get("deploy_like"):
        return None

    if resource.attributes.get("environment"):
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.deployment.environment.missing",
        category="operational_safety",
        severity="HIGH",
        title=f"CI/CD deployment job '{resource.name}' has no protected environment",
        impact="Deployment jobs without environments can bypass production approval and environment-specific controls.",
        recommendation="Attach deployment jobs to protected environments with required reviewers or equivalent release controls.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "job": resource.name,
            "environment": resource.attributes.get("environment"),
        },
        tags=["cicd", "deployment", "approval"],
    )


def workflow_pull_request_target_used(resource, context):
    triggers = resource.attributes.get("triggers", [])

    if "pull_request_target" not in triggers:
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.github.pull_request_target.used",
        category="operational_safety",
        severity="MEDIUM",
        title=f"Workflow '{resource.attributes.get('workflow')}' uses pull_request_target",
        impact="pull_request_target runs with elevated repository context and can be risky if untrusted code is checked out or executed.",
        recommendation="Use pull_request where possible, or strictly avoid executing untrusted fork code in pull_request_target workflows.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "triggers": triggers,
        },
        tags=["cicd", "github-actions", "supply-chain"],
    )


def workflow_permissions_write_all(resource, context):
    permissions = resource.attributes.get("permissions")

    if permissions != "write-all":
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.github.permissions.write_all",
        category="operational_safety",
        severity="HIGH",
        title=f"Workflow '{resource.attributes.get('workflow')}' grants write-all token permissions",
        impact="Broad CI token permissions increase blast radius if a workflow, action, or dependency is compromised.",
        recommendation="Use least-privilege GitHub token permissions at workflow and job level.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "permissions": permissions,
        },
        tags=["cicd", "github-actions", "least-privilege"],
    )


def workflow_third_party_actions_unpinned(resource, context):
    step_uses = resource.attributes.get("step_uses", [])
    unpinned = [
        action
        for action in step_uses
        if is_external_action(action) and not is_sha_pinned_action(action)
    ]

    if not unpinned:
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.github.third_party_actions.unpinned",
        category="operational_safety",
        severity="HIGH",
        title=f"Workflow '{resource.attributes.get('workflow')}' uses unpinned third-party actions",
        impact="Unpinned GitHub Actions can change unexpectedly and increase supply-chain risk during builds and deployments.",
        recommendation="Pin third-party actions to immutable commit SHAs and review updates through controlled dependency management.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "job": resource.name,
            "unpinned_actions": unpinned,
        },
        tags=["cicd", "github-actions", "supply-chain"],
    )


def deployment_timeout_missing(resource, context):
    if not resource.attributes.get("deploy_like"):
        return None

    timeout = resource.attributes.get("timeout_minutes")
    if timeout is not None:
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.deployment.timeout.missing",
        category="operational_safety",
        severity="MEDIUM",
        title=f"CI/CD deployment job '{resource.name}' has no timeout",
        impact="Deployment jobs without timeouts can hang indefinitely, block release pipelines, and delay rollback or approval decisions.",
        recommendation="Set timeout-minutes on deployment and release jobs so stalled steps fail fast and escalate predictably.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "job": resource.name,
            "timeout_minutes": timeout,
        },
        tags=["cicd", "deployment", "governance"],
    )


def deployment_concurrency_missing(resource, context):
    if not resource.attributes.get("deploy_like"):
        return None

    concurrency = resource.attributes.get("concurrency")
    if concurrency:
        return None

    return build_cicd_finding(
        resource=resource,
        rule_id="cicd.deployment.concurrency.missing",
        category="operational_safety",
        severity="MEDIUM",
        title=f"CI/CD deployment job '{resource.name}' has no concurrency guard",
        impact="Missing concurrency controls can allow overlapping deployments to the same environment and increase release collision risk.",
        recommendation="Define workflow or job concurrency for deploy-like jobs so only one environment mutation path runs at a time.",
        evidence={
            "workflow": resource.attributes.get("workflow"),
            "job": resource.name,
            "concurrency": concurrency,
        },
        tags=["cicd", "deployment", "concurrency"],
    )


def register(rule_id, category, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="cicd",
            category=category,
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["cicd_workflow_job"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "cicd.deployment.environment.missing",
    "operational_safety",
    "HIGH",
    "CI/CD deployment environment missing",
    "Detects deploy-like CI/CD jobs without protected deployment environments.",
    deployment_job_missing_environment,
    ["cicd", "deployment", "approval"],
)

register(
    "cicd.github.pull_request_target.used",
    "operational_safety",
    "MEDIUM",
    "GitHub Actions pull_request_target used",
    "Detects workflows using pull_request_target.",
    workflow_pull_request_target_used,
    ["cicd", "github-actions", "supply-chain"],
)

register(
    "cicd.github.permissions.write_all",
    "operational_safety",
    "HIGH",
    "GitHub Actions write-all permissions",
    "Detects workflows granting write-all token permissions.",
    workflow_permissions_write_all,
    ["cicd", "github-actions", "least-privilege"],
)
register(
    "cicd.github.third_party_actions.unpinned",
    "operational_safety",
    "HIGH",
    "GitHub Actions third-party actions are not SHA pinned",
    "Detects external GitHub Actions references that are not pinned to immutable commit SHAs.",
    workflow_third_party_actions_unpinned,
    ["cicd", "github-actions", "supply-chain"],
)
register(
    "cicd.deployment.timeout.missing",
    "operational_safety",
    "MEDIUM",
    "CI/CD deployment timeout missing",
    "Detects deploy-like jobs without timeout-minutes.",
    deployment_timeout_missing,
    ["cicd", "deployment", "governance"],
)
register(
    "cicd.deployment.concurrency.missing",
    "operational_safety",
    "MEDIUM",
    "CI/CD deployment concurrency missing",
    "Detects deploy-like jobs without concurrency protection.",
    deployment_concurrency_missing,
    ["cicd", "deployment", "concurrency"],
)
