import base64
import json
import urllib.error
import urllib.parse
import urllib.request

import yaml


UNSAFE_COMPATIBILITY = {"NONE", "DISABLED"}


def analyze_schema_registry_config(path, timeout=5):
    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}

    registry = config.get("schema_registry", config)
    base_url = registry.get("url")

    if not base_url:
        return [
            schema_registry_finding(
                "schema_registry.config.url.missing",
                "ERROR",
                "Schema Registry URL is missing",
                "Beacon cannot query Schema Registry without a base URL.",
                "Set schema_registry.url in the collector config.",
                path,
                {"config": path},
            )
        ]

    findings = [
        schema_registry_finding(
            "schema_registry.runtime.read_only_mode",
            "INFO",
            "Beacon Schema Registry connector is running in read-only diagnostic mode",
            "Beacon will only query Schema Registry metadata and compatibility settings.",
            "No subject, schema, or compatibility mutation operation will be performed.",
            path,
            {"mode": "read_only", "mutation_allowed": False},
        )
    ]

    try:
        subjects = query_schema_registry(base_url, "/subjects", registry, timeout)
    except Exception as error:
        findings.append(query_failed(path, "/subjects", error))
        return findings

    subject_set = set(subjects or [])
    findings.extend(check_expected_topic_subjects(registry, subject_set, path))

    try:
        global_config = query_schema_registry(base_url, "/config", registry, timeout)
        compatibility = normalize_compatibility(global_config)
        if compatibility in UNSAFE_COMPATIBILITY:
            findings.append(
                schema_registry_finding(
                    "schema_registry.compatibility.global_unsafe",
                    "HIGH",
                    f"Schema Registry global compatibility is unsafe: {compatibility}",
                    "Unsafe global compatibility can allow producer schema changes that break consumers.",
                    "Use BACKWARD, FULL, or an approved compatibility mode for production event schemas.",
                    path,
                    {"compatibility": compatibility},
                )
            )
    except Exception as error:
        findings.append(query_failed(path, "/config", error))

    for subject in selected_subjects(subjects, registry.get("max_subjects", 50)):
        findings.extend(analyze_subject(base_url, registry, subject, path, timeout))

    return findings


def analyze_subject(base_url, registry, subject, source, timeout):
    findings = []
    encoded_subject = urllib.parse.quote(subject, safe="")

    try:
        config = query_schema_registry(
            base_url, f"/config/{encoded_subject}", registry, timeout
        )
        compatibility = normalize_compatibility(config)
        if compatibility in UNSAFE_COMPATIBILITY:
            findings.append(
                schema_registry_finding(
                    "schema_registry.subject.compatibility.unsafe",
                    "HIGH",
                    f"Schema subject '{subject}' has unsafe compatibility",
                    "Unsafe subject compatibility can break consumers during producer deployments.",
                    "Use BACKWARD, FULL, or an approved subject-level compatibility mode.",
                    source,
                    {"subject": subject, "compatibility": compatibility},
                )
            )
    except urllib.error.HTTPError as error:
        if error.code != 404:
            findings.append(query_failed(source, f"/config/{encoded_subject}", error))
    except Exception as error:
        findings.append(query_failed(source, f"/config/{encoded_subject}", error))

    try:
        latest = query_schema_registry(
            base_url, f"/subjects/{encoded_subject}/versions/latest", registry, timeout
        )
        if not latest.get("schema"):
            findings.append(
                schema_registry_finding(
                    "schema_registry.subject.latest_schema.missing",
                    "ERROR",
                    f"Schema subject '{subject}' latest version has no schema body",
                    "Beacon cannot validate deployment safety without a latest schema body.",
                    "Check Schema Registry subject health and permissions.",
                    source,
                    {"subject": subject, "latest": latest},
                )
            )
        if not latest.get("schemaType"):
            findings.append(
                schema_registry_finding(
                    "schema_registry.subject.schema_type.missing",
                    "LOW",
                    f"Schema subject '{subject}' does not expose schema type",
                    "Missing schema type can make schema governance and tooling behavior less explicit.",
                    "Set or verify schema type where the platform supports it.",
                    source,
                    {"subject": subject, "version": latest.get("version")},
                )
            )
    except Exception as error:
        findings.append(
            schema_registry_finding(
                "schema_registry.subject.latest_version.unavailable",
                "ERROR",
                f"Schema subject '{subject}' latest version is unavailable",
                "Beacon could not inspect the latest schema version for this subject.",
                "Check Schema Registry permissions, subject existence, and API health.",
                source,
                {"subject": subject, "error": str(error)},
            )
        )

    return findings


def check_expected_topic_subjects(registry, subject_set, source):
    findings = []

    for item in registry.get("expected_topics", []) or []:
        topic = item.get("name")
        expected_subjects = item.get("subjects") or [f"{topic}-key", f"{topic}-value"]

        missing = [
            subject for subject in expected_subjects if subject not in subject_set
        ]

        if missing:
            findings.append(
                schema_registry_finding(
                    "schema_registry.topic.subject.missing",
                    "HIGH",
                    f"Kafka topic '{topic}' is missing expected schema subjects",
                    "Missing Schema Registry subjects can indicate unmanaged producers or consumers without schema contracts.",
                    "Register and enforce expected key/value subjects for production topics.",
                    source,
                    {
                        "topic": topic,
                        "expected_subjects": expected_subjects,
                        "missing_subjects": missing,
                    },
                )
            )

    return findings


def selected_subjects(subjects, max_subjects):
    return list(subjects or [])[: max(0, int(max_subjects or 0))]


def normalize_compatibility(config):
    value = config.get("compatibilityLevel", config.get("compatibility"))
    return str(value or "").upper()


def query_schema_registry(base_url, path, registry, timeout=5):
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url)

    for key, value in auth_headers(registry).items():
        request.add_header(key, value)

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def auth_headers(registry):
    auth = registry.get("auth", {}) or {}
    auth_type = auth.get("type")

    if auth_type == "bearer_token":
        token = auth.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    if auth_type == "basic":
        username = auth.get("username", "")
        password = auth.get("password", "")
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    return {}


def query_failed(source, endpoint, error):
    return schema_registry_finding(
        "schema_registry.query.failed",
        "ERROR",
        f"Schema Registry query failed for {endpoint}",
        "Beacon could not collect one or more Schema Registry signals.",
        "Check the Schema Registry URL, credentials, network access, and API permissions.",
        source,
        {"endpoint": endpoint, "error": str(error)},
    )


def schema_registry_finding(
    rule_id, severity, title, impact, recommendation, file, evidence
):
    return {
        "rule_id": rule_id,
        "domain": "kafka",
        "category": "operational_safety",
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file,
        "evidence": evidence,
        "tags": ["schema-registry", "kafka", "runtime"],
    }
