from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def build_iam_finding(
    resource,
    rule_id,
    severity,
    title,
    impact,
    recommendation,
    evidence,
    tags=None,
):
    return Finding(
        rule_id=rule_id,
        domain="cloud_identity",
        category="operational_safety",
        severity=severity,
        title=title,
        impact=impact,
        recommendation=recommendation,
        file=resource.source,
        evidence=evidence,
        tags=tags or [],
    )


def wildcard_permissions(resource, context):
    raw_config = resource.attributes.get("raw_config", "")

    if (
        '"Action":"*"' not in raw_config
        and '"Resource":"*"' not in raw_config
        and "*:*" not in raw_config
    ):
        return None

    return build_iam_finding(
        resource=resource,
        rule_id="iam.permissions.wildcard",
        severity="HIGH",
        title=f"Wildcard IAM permissions detected in '{resource.name}'",
        impact="Wildcard permissions increase blast radius during credential misuse.",
        recommendation="Apply least-privilege permissions and avoid wildcard access.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource.attributes.get("provider_resource_type"),
            "pattern": "wildcard_permission",
        },
        tags=["iam", "security", "least-privilege"],
    )


def admin_or_owner_excessive(resource, context):
    raw_config = resource.attributes.get("raw_config", "")

    if (
        "roles/owner" not in raw_config
        and "Owner" not in raw_config
        and "AdministratorAccess" not in raw_config
    ):
        return None

    return build_iam_finding(
        resource=resource,
        rule_id="iam.admin_or_owner.excessive",
        severity="HIGH",
        title=f"Administrative cloud access detected in '{resource.name}'",
        impact="Owner/admin-level access increases operational blast radius.",
        recommendation="Restrict admin access to approved platform administrators only.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource.attributes.get("provider_resource_type"),
            "pattern": "admin_or_owner_access",
        },
        tags=["iam", "security", "admin-access"],
    )


def register(rule_id, severity, title, description, evaluator, tags):
    registry.register(
        Rule(
            rule_id=rule_id,
            domain="cloud_identity",
            category="operational_safety",
            severity=severity,
            title=title,
            description=description,
            supported_resource_types=["iam_policy"],
            evaluator=evaluator,
            tags=tags,
        )
    )


register(
    "iam.permissions.wildcard",
    "HIGH",
    "Wildcard IAM permissions",
    "Detects wildcard IAM permissions.",
    wildcard_permissions,
    ["iam", "security", "least-privilege"],
)

register(
    "iam.admin_or_owner.excessive",
    "HIGH",
    "Excessive admin or owner permissions",
    "Detects excessive admin or owner permissions.",
    admin_or_owner_excessive,
    ["iam", "security", "admin-access"],
)
