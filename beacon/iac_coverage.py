"""IaC coverage readiness analysis.

This module compares cloud inventory exports against Terraform state and
ownership metadata. It is intentionally file-based for the first release: Beacon
does not connect to cloud accounts or mutate Terraform state here.
"""

import json
from pathlib import Path

import yaml

SENSITIVE_RESOURCE_TYPES = {
    "aws_db_instance",
    "aws_opensearch_domain",
    "aws_elasticsearch_domain",
    "aws_s3_bucket",
    "aws_efs_file_system",
    "aws_eks_cluster",
    "aws_msk_cluster",
}

AWS_CONFIG_TYPE_MAP = {
    "AWS::EC2::Instance": "aws_instance",
    "AWS::Elasticsearch::Domain": "aws_elasticsearch_domain",
    "AWS::OpenSearchService::Domain": "aws_opensearch_domain",
    "AWS::RDS::DBInstance": "aws_db_instance",
    "AWS::S3::Bucket": "aws_s3_bucket",
    "AWS::EFS::FileSystem": "aws_efs_file_system",
    "AWS::EKS::Cluster": "aws_eks_cluster",
    "AWS::MSK::Cluster": "aws_msk_cluster",
}

ARN_SERVICE_TYPE_MAP = {
    "ec2": "aws_instance",
    "es": "aws_opensearch_domain",
    "opensearch": "aws_opensearch_domain",
    "rds": "aws_db_instance",
    "s3": "aws_s3_bucket",
    "elasticfilesystem": "aws_efs_file_system",
    "eks": "aws_eks_cluster",
    "kafka": "aws_msk_cluster",
}


def analyze_iac_coverage(cloud_inventory_path, terraform_state_path, owners_path=None):
    inventory = load_structured_file(cloud_inventory_path)
    state = load_structured_file(terraform_state_path)
    owners = load_structured_file(owners_path) if owners_path else {}

    cloud_resources = normalize_cloud_inventory(inventory, cloud_inventory_path)
    managed_keys = terraform_state_keys(state)
    owners_index = build_owners_index(owners)

    findings = []

    for resource in cloud_resources:
        if resource_keys(resource) & managed_keys:
            continue

        findings.append(unmanaged_resource_finding(resource, cloud_inventory_path))

        if not has_owner(resource, owners_index):
            findings.append(unmanaged_missing_owner_finding(resource, cloud_inventory_path))

        if has_recent_activity(resource):
            findings.append(unmanaged_recent_activity_finding(resource, cloud_inventory_path))

        if is_publicly_exposed(resource):
            findings.append(unmanaged_public_exposure_finding(resource, cloud_inventory_path))

        if is_sensitive_resource(resource):
            findings.append(unmanaged_sensitive_resource_finding(resource, cloud_inventory_path))

    return findings


def load_structured_file(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".json":
        return json.loads(text)

    return yaml.safe_load(text) or {}


def normalize_cloud_inventory(data, source):
    if isinstance(data, list):
        raw_resources = data
    elif not isinstance(data, dict):
        return []
    else:
        raw_resources = extract_inventory_resources(data)

    resources = []
    for item in raw_resources or []:
        if not isinstance(item, dict):
            continue

        resources.append(normalize_inventory_item(item, source))

    return resources


def extract_inventory_resources(data):
    if isinstance(data.get("cloud_inventory"), dict):
        nested = data["cloud_inventory"]
        for key in ("resources", "items", "rows"):
            if isinstance(nested.get(key), list):
                return nested[key]

    for key in (
        "resources",
        "Resources",
        "items",
        "Items",
        "rows",
        "Rows",
        "configurationItems",
    ):
        if isinstance(data.get(key), list):
            return data[key]

    return []


def normalize_inventory_item(item, source):
    config = normalize_config(item)
    arn = first_present(
        item.get("arn"),
        item.get("Arn"),
        item.get("ARN"),
        config.get("arn"),
        first_list_value(item.get("akas")),
        first_list_value(item.get("Akas")),
    )
    resource_type = normalize_resource_type(
        first_present(
            item.get("type"),
            item.get("resource_type"),
            item.get("resourceType"),
            item.get("ResourceType"),
            item.get("resourceTypeName"),
            item.get("__table"),
            item.get("table"),
        ),
        arn,
    )
    tags = normalize_tags(first_present(item.get("tags"), item.get("Tags"), config.get("tags")))
    name = first_present(
        item.get("name"),
        item.get("Name"),
        item.get("title"),
        item.get("Title"),
        item.get("resourceName"),
        item.get("ResourceName"),
        item.get("resourceId"),
        item.get("ResourceId"),
        item.get("id"),
        item.get("Id"),
        config.get("name"),
        config.get("bucket"),
        config.get("domain_name"),
        config.get("DBInstanceIdentifier"),
        arn_resource_name(arn),
        "unknown",
    )
    resource_id = first_present(
        item.get("id"),
        item.get("Id"),
        item.get("resourceId"),
        item.get("ResourceId"),
        config.get("id"),
        config.get("resourceId"),
    )

    return {
        "type": resource_type,
        "name": name,
        "id": resource_id,
        "arn": arn,
        "account_id": first_present(
            item.get("account_id"),
            item.get("account"),
            item.get("accountId"),
            item.get("AccountId"),
            item.get("AwsAccountId"),
            config.get("account_id"),
            config.get("accountId"),
            arn_account_id(arn),
        ),
        "region": first_present(
            item.get("region"),
            item.get("Region"),
            item.get("awsRegion"),
            item.get("AwsRegion"),
            config.get("region"),
            config.get("awsRegion"),
            arn_region(arn),
        ),
        "tags": tags,
        "config": {**config, **{k: v for k, v in item.items() if k != "config"}},
        "source": str(source),
    }


def normalize_config(item):
    raw_config = first_present(
        item.get("config"),
        item.get("configuration"),
        item.get("Configuration"),
        {},
    )
    if isinstance(raw_config, str):
        try:
            parsed = json.loads(raw_config)
        except json.JSONDecodeError:
            return {"raw_configuration": raw_config}
        return parsed if isinstance(parsed, dict) else {"configuration": parsed}

    return raw_config if isinstance(raw_config, dict) else {}


def normalize_resource_type(value, arn=None):
    if value in AWS_CONFIG_TYPE_MAP:
        return AWS_CONFIG_TYPE_MAP[value]

    if isinstance(value, str):
        normalized = value.strip()
        if normalized.startswith("aws_"):
            return normalized
        if normalized.startswith("AWS::"):
            return normalized.lower().replace("::", "_")
        if normalized:
            return normalized

    service = arn_service(arn)
    return ARN_SERVICE_TYPE_MAP.get(service, service)


def normalize_tags(value):
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        tags = {}
        for item in value:
            if isinstance(item, dict):
                key = item.get("key") or item.get("Key")
                tag_value = item.get("value") or item.get("Value")
                if key:
                    tags[str(key)] = tag_value
        return tags

    return {}


def first_present(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None


def first_list_value(value):
    return value[0] if isinstance(value, list) and value else None


def arn_parts(arn):
    if not isinstance(arn, str) or not arn.startswith("arn:"):
        return []
    return arn.split(":", 5)


def arn_service(arn):
    parts = arn_parts(arn)
    return parts[2] if len(parts) > 2 else None


def arn_region(arn):
    parts = arn_parts(arn)
    return parts[3] if len(parts) > 3 else None


def arn_account_id(arn):
    parts = arn_parts(arn)
    return parts[4] if len(parts) > 4 else None


def arn_resource_name(arn):
    parts = arn_parts(arn)
    if len(parts) < 6:
        return None
    resource = parts[5]
    return resource.rsplit("/", 1)[-1].rsplit(":", 1)[-1]


def terraform_state_keys(data):
    keys = set()

    for item in iter_terraform_resources(data):
        resource_type = item.get("type")
        name = item.get("name")
        values = item.get("values") or {}

        add_key(keys, "type_name", resource_type, name)
        add_key(keys, "id", resource_type, values.get("id"))
        add_key(keys, "arn", resource_type, values.get("arn"))

        physical_name = values.get("name") or values.get("bucket") or values.get("domain_name")
        add_key(keys, "physical_name", resource_type, physical_name)

    return keys


def iter_terraform_resources(data):
    if not isinstance(data, dict):
        return

    for resource in data.get("resources", []):
        yield {
            "type": resource.get("type"),
            "name": resource.get("name"),
            "values": (
                resource.get("instances", [{}])[0].get("attributes", {})
                if resource.get("instances")
                else {}
            ),
        }

    values = data.get("values") or data.get("planned_values") or {}
    yield from iter_terraform_value_resources(values)


def iter_terraform_value_resources(values):
    root = values.get("root_module") if isinstance(values, dict) else None
    if not isinstance(root, dict):
        return

    yield from iter_module_resources(root)


def iter_module_resources(module):
    for resource in module.get("resources", []) or []:
        yield {
            "type": resource.get("type"),
            "name": resource.get("name"),
            "values": resource.get("values") or {},
        }

    for child in module.get("child_modules", []) or []:
        yield from iter_module_resources(child)


def add_key(keys, kind, resource_type, value):
    if resource_type and value:
        keys.add((kind, str(resource_type), normalize_value(value)))


def resource_keys(resource):
    keys = set()
    resource_type = resource.get("type")
    config = resource.get("config") or {}

    add_key(keys, "type_name", resource_type, resource.get("name"))
    add_key(keys, "id", resource_type, resource.get("id") or config.get("id"))
    add_key(keys, "arn", resource_type, resource.get("arn") or config.get("arn"))

    physical_name = (
        config.get("name")
        or config.get("bucket")
        or config.get("domain_name")
        or resource.get("name")
    )
    add_key(keys, "physical_name", resource_type, physical_name)

    return keys


def normalize_value(value):
    return str(value).strip('"').lower()


def build_owners_index(data):
    if not isinstance(data, dict):
        return {}

    raw_owners = data.get("owners") or data.get("resources") or {}
    if isinstance(raw_owners, list):
        return {
            str(item.get("resource") or item.get("name") or item.get("id")): item
            for item in raw_owners
            if isinstance(item, dict)
        }

    return raw_owners if isinstance(raw_owners, dict) else {}


def has_owner(resource, owners_index):
    tags = resource.get("tags") or {}
    config = resource.get("config") or {}
    owner_keys = {"owner", "team", "service", "application", "app"}

    if any(tags.get(key) for key in owner_keys):
        return True

    if any(config.get(key) for key in owner_keys):
        return True

    identifiers = {
        str(resource.get("name")),
        str(resource.get("id")),
        str(resource.get("arn")),
        f"{resource.get('type')}.{resource.get('name')}",
    }
    return any(identifier in owners_index for identifier in identifiers if identifier)


def has_recent_activity(resource):
    config = resource.get("config") or {}
    activity = (
        resource.get("activity_30d")
        or resource.get("recent_activity")
        or config.get("activity_30d")
        or config.get("recent_activity")
    )
    cost = (
        resource.get("cost_30d")
        or resource.get("monthly_cost")
        or config.get("cost_30d")
        or config.get("monthly_cost")
    )

    return truthy(activity) or numeric_gt_zero(cost)


def truthy(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "yes", "active", "detected"}
    return bool(value)


def numeric_gt_zero(value):
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def is_publicly_exposed(resource):
    config = resource.get("config") or {}
    if config.get("publicly_accessible") is True or config.get("public") is True:
        return True

    if resource.get("type") in {"aws_opensearch_domain", "aws_elasticsearch_domain"}:
        vpc_options = config.get("VPCOptions") or config.get("vpc_options") or {}
        has_vpc = bool(
            vpc_options.get("VPCId")
            or vpc_options.get("VPCOptions")
            or vpc_options.get("SubnetIds")
        )
        if config.get("Endpoint") and not has_vpc:
            return True

    exposure = str(config.get("network_exposure") or resource.get("network_exposure") or "").lower()
    if exposure in {"public", "internet", "internet-facing"}:
        return True

    for rule in config.get("ingress", []) or []:
        cidrs = rule.get("cidr_blocks") or []
        ipv6 = rule.get("ipv6_cidr_blocks") or []
        if "0.0.0.0/0" in cidrs or "::/0" in ipv6:
            return True

    return False


def is_sensitive_resource(resource):
    return resource.get("type") in SENSITIVE_RESOURCE_TYPES


def resource_label(resource):
    parts = [resource.get("type"), resource.get("name")]
    location = "/".join(
        part for part in [resource.get("account_id"), resource.get("region")] if part
    )
    label = ".".join(part for part in parts if part)
    return f"{label} ({location})" if location else label


def base_evidence(resource):
    config = resource.get("config") or {}
    return {
        "resource_type": resource.get("type"),
        "resource_name": resource.get("name"),
        "resource_id": resource.get("id"),
        "arn": resource.get("arn"),
        "account_id": resource.get("account_id"),
        "region": resource.get("region"),
        "tags": resource.get("tags") or {},
        "cost_30d": resource.get("cost_30d") or config.get("cost_30d"),
        "activity_30d": resource.get("activity_30d") or config.get("activity_30d"),
        "terraform_state_match": "none",
    }


def finding(rule_id, severity, title, impact, recommendation, resource, file, evidence=None):
    return {
        "rule_id": rule_id,
        "domain": "iac_coverage",
        "category": "operational_safety",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": str(file),
        "evidence": {**base_evidence(resource), **(evidence or {})},
        "tags": ["iac-coverage", "terraform", "cloud-inventory"],
    }


def unmanaged_resource_finding(resource, file):
    return finding(
        "iac_coverage.resource.unmanaged",
        "HIGH",
        f"Cloud resource is not managed by Terraform: {resource_label(resource)}",
        "Infrastructure outside Terraform state can bypass review, ownership, drift control, and production readiness gates.",
        "Classify the resource before import or deletion. Recommended disposition: owner review, then import into Terraform or document an approved exception.",
        resource,
        file,
        {"recommended_disposition": "owner_review"},
    )


def unmanaged_missing_owner_finding(resource, file):
    return finding(
        "iac_coverage.resource.owner_missing",
        "HIGH",
        f"Unmanaged cloud resource has no owner metadata: {resource_label(resource)}",
        "Unowned unmanaged infrastructure slows incident response, cost cleanup, and deletion/import decisions.",
        "Add owner/application tags or ownership registry metadata before deciding whether to import, delete, or quarantine the resource.",
        resource,
        file,
        {"recommended_disposition": "tag_and_review"},
    )


def unmanaged_recent_activity_finding(resource, file):
    return finding(
        "iac_coverage.resource.active_unmanaged",
        "HIGH",
        f"Unmanaged cloud resource has recent activity or cost: {resource_label(resource)}",
        "Active unmanaged infrastructure may be serving production traffic or accumulating cost without change control.",
        "Do not delete blindly. Review activity, dependencies, and owner before import, quarantine, or removal.",
        resource,
        file,
        {"recommended_disposition": "do_not_touch_until_reviewed"},
    )


def unmanaged_public_exposure_finding(resource, file):
    return finding(
        "iac_coverage.resource.public_unmanaged",
        "CRITICAL",
        f"Unmanaged cloud resource appears publicly exposed: {resource_label(resource)}",
        "Public unmanaged infrastructure can create unknown security and operational blast radius.",
        "Prioritize security review, restrict exposure if unauthorized, then import or document an approved exception.",
        resource,
        file,
        {"recommended_disposition": "security_review"},
    )


def unmanaged_sensitive_resource_finding(resource, file):
    return finding(
        "iac_coverage.resource.sensitive_unmanaged",
        "HIGH",
        f"Sensitive cloud resource is unmanaged: {resource_label(resource)}",
        "Databases, search clusters, storage, and platform clusters outside Terraform state can hide backup, encryption, deletion, and ownership risk.",
        "Review blast radius and recovery posture before import or deletion. Prefer import for active production resources.",
        resource,
        file,
        {"recommended_disposition": "import_or_exception_review"},
    )
