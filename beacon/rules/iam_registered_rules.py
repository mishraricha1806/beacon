from beacon.engine.models import Finding, Rule
from beacon.engine.registry import registry


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_aws_policy_document(config):
    if not isinstance(config, dict):
        return {}

    policy = config.get("policy")
    if isinstance(policy, dict):
        return policy

    if isinstance(policy, str):
        try:
            import json

            loaded = json.loads(policy)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return {}

    if "Statement" in config:
        return config

    return {}


def extract_aws_statements(config):
    document = extract_aws_policy_document(config)
    return ensure_list(document.get("Statement")) if document else []


def aws_statement_has_wildcards(statement):
    effect = str(statement.get("Effect", "Allow")).lower()
    if effect != "allow":
        return False

    actions = ensure_list(statement.get("Action") or statement.get("NotAction"))
    resources = ensure_list(statement.get("Resource") or statement.get("NotResource"))

    return any(value in {"*", "*:*"} for value in actions + resources)


def gcp_role(config):
    if not isinstance(config, dict):
        return None
    return config.get("role")


def azure_role_name(config):
    if not isinstance(config, dict):
        return None
    return config.get("role_definition_name") or config.get("role_definition_id")


def raw_config_contains_wildcard(config):
    text = str(config)
    return (
        '"Action":"*"' in text
        or '"Resource":"*"' in text
        or "*:*" in text
        or "Action': '*'" in text
        or "Resource': '*'" in text
    )


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
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    wildcard_statement = None
    if resource_type == "aws_iam_policy":
        wildcard_statement = next(
            (
                statement
                for statement in extract_aws_statements(config)
                if isinstance(statement, dict) and aws_statement_has_wildcards(statement)
            ),
            None,
        )
        if wildcard_statement is None and raw_config_contains_wildcard(config):
            wildcard_statement = {"raw_match": True}

    if wildcard_statement is None:
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
            "resource_type": resource_type,
            "pattern": "wildcard_permission",
            "statement": wildcard_statement,
        },
        tags=["iam", "security", "least-privilege"],
    )


def admin_or_owner_excessive(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    matched_pattern = None
    if resource_type == "aws_iam_policy":
        if any(
            isinstance(statement, dict) and aws_statement_has_wildcards(statement)
            for statement in extract_aws_statements(config)
        ):
            matched_pattern = "aws_admin_equivalent"
        elif raw_config_contains_wildcard(config):
            matched_pattern = "aws_admin_equivalent"
        elif "AdministratorAccess" in str(config):
            matched_pattern = "aws_managed_admin"
    elif resource_type == "google_project_iam_binding":
        role = str(gcp_role(config) or "")
        if role in {"roles/owner", "roles/editor"} or role.endswith(".admin"):
            matched_pattern = role
    elif resource_type == "azurerm_role_assignment":
        role_name = str(azure_role_name(config) or "")
        if any(
            keyword in role_name
            for keyword in ["Owner", "Contributor", "User Access Administrator"]
        ):
            matched_pattern = role_name

    if not matched_pattern:
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
            "resource_type": resource_type,
            "pattern": matched_pattern,
        },
        tags=["iam", "security", "admin-access"],
    )


def managed_admin_policy_attached(resource, context):
    resource_type = resource.attributes.get("provider_resource_type")
    config = resource.attributes.get("config", {})

    if resource_type not in {
        "aws_iam_role_policy_attachment",
        "aws_iam_user_policy_attachment",
        "aws_iam_group_policy_attachment",
    }:
        return None

    policy_arn = str(config.get("policy_arn") or "").strip('"')
    admin_managed_policies = {
        "arn:aws:iam::aws:policy/AdministratorAccess",
        "arn:aws:iam::aws:policy/PowerUserAccess",
        "arn:aws:iam::aws:policy/IAMFullAccess",
    }

    if policy_arn not in admin_managed_policies:
        return None

    return build_iam_finding(
        resource=resource,
        rule_id="iam.managed_admin_policy.attached",
        severity="HIGH",
        title=f"Administrative managed IAM policy attached in '{resource.name}'",
        impact="Broad AWS managed policies increase blast radius for compromised identities and frequently accumulate on node, workload, or automation roles.",
        recommendation="Replace broad managed policies with scoped least-privilege policies and review node/workload role attachments regularly.",
        evidence={
            "resource_name": resource.name,
            "resource_type": resource_type,
            "policy_arn": policy_arn,
            "role": config.get("role"),
            "user": config.get("user"),
            "group": config.get("group"),
        },
        tags=["iam", "security", "managed-policy", "least-privilege"],
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

register(
    "iam.managed_admin_policy.attached",
    "HIGH",
    "Administrative managed IAM policy attached",
    "Detects broad AWS managed policies attached to roles, users, or groups.",
    managed_admin_policy_attached,
    ["iam", "security", "managed-policy", "least-privilege"],
)
