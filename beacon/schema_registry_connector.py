import base64
import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

from beacon.input_validation import missing_path_finding, path_missing

UNSAFE_COMPATIBILITY = {"NONE", "DISABLED"}
LOGGER = logging.getLogger(__name__)


def analyze_schema_registry_config(path, timeout=5):
    started = time.monotonic()
    LOGGER.info(
        "schema_registry.start path=%s timeout=%ss",
        path,
        timeout,
    )

    if path_missing(path):
        LOGGER.warning("schema_registry.path_missing path=%s", path)
        return [missing_path_finding(path)]

    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}

    registry = config.get("schema_registry", config)
    base_url = registry.get("url")
    max_subjects = registry.get("max_subjects", 50)
    LOGGER.info(
        "schema_registry.config_loaded base_url=%s max_subjects=%s auth_type=%s tls=%s",
        safe_base_url(base_url),
        max_subjects,
        (registry.get("auth") or {}).get("type") or "none",
        bool(registry.get("tls") or {}),
    )

    if not base_url:
        LOGGER.warning("schema_registry.missing_url path=%s", path)
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
        LOGGER.info(
            "schema_registry.subjects_failed error=%s",
            error,
            exc_info=True,
        )
        findings.append(query_failed(path, "/subjects", error))
        return findings

    subject_set = set(subjects or [])
    LOGGER.info("schema_registry.subjects_loaded count=%s", len(subject_set))
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
        LOGGER.info(
            "schema_registry.global_config_failed error=%s",
            error,
            exc_info=True,
        )
        findings.append(query_failed(path, "/config", error))

    selected = selected_subjects(subjects, max_subjects)
    LOGGER.info("schema_registry.subject_analysis count=%s", len(selected))
    for subject in selected:
        findings.extend(analyze_subject(base_url, registry, subject, path, timeout))

    LOGGER.info(
        "schema_registry.complete findings=%s elapsed=%.2fs",
        len(findings),
        time.monotonic() - started,
    )
    return findings


def analyze_subject(base_url, registry, subject, source, timeout):
    findings = []
    encoded_subject = urllib.parse.quote(subject, safe="")
    LOGGER.info("schema_registry.subject.start subject=%s", subject)

    try:
        config = query_schema_registry(base_url, f"/config/{encoded_subject}", registry, timeout)
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
            LOGGER.info(
                "schema_registry.subject_config_failed subject=%s error=%s",
                subject,
                error,
                exc_info=True,
            )
            findings.append(query_failed(source, f"/config/{encoded_subject}", error))
    except Exception as error:
        LOGGER.info(
            "schema_registry.subject_config_failed subject=%s error=%s",
            subject,
            error,
            exc_info=True,
        )
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
        LOGGER.info(
            "schema_registry.subject_latest_failed subject=%s error=%s",
            subject,
            error,
            exc_info=True,
        )
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

    LOGGER.info(
        "schema_registry.subject.complete subject=%s findings=%s",
        subject,
        len(findings),
    )
    return findings


def check_expected_topic_subjects(registry, subject_set, source):
    findings = []

    for item in registry.get("expected_topics", []) or []:
        topic = item.get("name")
        expected_subjects = item.get("subjects") or [f"{topic}-key", f"{topic}-value"]

        missing = [subject for subject in expected_subjects if subject not in subject_set]

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
    started = time.monotonic()
    LOGGER.info(
        "schema_registry.query.start endpoint=%s url=%s timeout=%ss",
        path,
        safe_url(url),
        timeout,
    )

    for key, value in auth_headers(registry).items():
        request.add_header(key, value)

    context = build_ssl_context(registry)
    try:
        if context:
            response_handle = urllib.request.urlopen(request, timeout=timeout, context=context)
        else:
            response_handle = urllib.request.urlopen(request, timeout=timeout)

        with response_handle as response:
            payload = json.loads(response.read().decode("utf-8"))
            LOGGER.info(
                "schema_registry.query.complete endpoint=%s elapsed=%.2fs",
                path,
                time.monotonic() - started,
            )
            return payload
    except Exception:
        LOGGER.info(
            "schema_registry.query.failed endpoint=%s elapsed=%.2fs",
            path,
            time.monotonic() - started,
        )
        raise


def build_ssl_context(registry):
    tls = registry.get("tls", {}) or {}
    auth = registry.get("auth", {}) or {}

    if auth.get("type") in {"mtls", "ssl"}:
        tls = {**auth, **tls}

    ca_cert = tls.get("ca_cert")
    client_cert = tls.get("client_cert")
    client_key = tls.get("client_key")

    if not any([ca_cert, client_cert, client_key]):
        return None

    LOGGER.info(
        "schema_registry.tls_context ca_cert=%s client_cert=%s client_key=%s",
        bool(ca_cert),
        bool(client_cert),
        bool(client_key),
    )
    context = ssl.create_default_context(cafile=ca_cert)
    if client_cert:
        context.load_cert_chain(certfile=client_cert, keyfile=client_key)

    return context


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


def safe_url(url):
    parsed = urllib.parse.urlsplit(url or "")
    if not parsed.scheme or not parsed.netloc:
        return url
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def safe_base_url(url):
    parsed = urllib.parse.urlsplit(url or "")
    if not parsed.scheme or not parsed.netloc:
        return url
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


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


def schema_registry_finding(rule_id, severity, title, impact, recommendation, file, evidence):
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
