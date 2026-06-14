import json

import yaml

from beacon.input_validation import missing_path_finding, path_missing
from beacon.kafka_runtime_connector import acl_evidence, finding, is_broad_allow_acl


def analyze_kafka_acl_file(path):
    if path_missing(path):
        return [missing_path_finding(path)]

    with open(path, "r") as f:
        if path.endswith(".json"):
            data = json.load(f) or {}
        else:
            data = yaml.safe_load(f) or {}

    acls = normalize_acl_export(data)

    if not acls:
        return [
            finding(
                "HIGH",
                "Kafka ACL export is empty",
                "An empty ACL export can mean authorization is not enforced or the export is incomplete.",
                "Verify authorizer configuration and export all production ACLs for review.",
                rule_id="kafka.acl.export.empty",
                category="operational_safety",
                evidence={"acl_count": 0, "source": path},
                confidence="MEDIUM",
            )
        ]

    broad_acls = [acl_evidence(acl) for acl in acls if is_broad_allow_acl(acl)]

    if broad_acls:
        return [
            finding(
                "HIGH",
                "Kafka ACL export includes broad allow permissions",
                "Broad ACLs can give users or services access beyond the intended topic or consumer-group blast radius.",
                "Replace wildcard or all-operation ACLs with scoped topic, group, and transactional-id permissions.",
                rule_id="kafka.acl.export.broad_allow",
                category="operational_safety",
                evidence={
                    "acl_count": len(acls),
                    "broad_acl_count": len(broad_acls),
                    "broad_acls": broad_acls[:10],
                    "source": path,
                },
                confidence="HIGH",
            )
        ]

    return [
        finding(
            "LOW",
            "Kafka ACL export inspected",
            "Beacon inspected the ACL export and did not detect broad allow patterns.",
            "Continue reviewing ACL exports during production readiness checks.",
            rule_id="kafka.acl.export.inspected",
            category="operational_safety",
            evidence={"acl_count": len(acls), "source": path},
            confidence="HIGH",
        )
    ]


def normalize_acl_export(data):
    if isinstance(data, list):
        return data

    for key in ("kafka_acls", "acls", "acl_bindings"):
        if isinstance(data.get(key), list):
            return data[key]

    kafka = data.get("kafka") if isinstance(data.get("kafka"), dict) else {}
    if isinstance(kafka.get("acls"), list):
        return kafka["acls"]

    return []
