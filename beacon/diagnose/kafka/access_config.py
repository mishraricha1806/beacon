import fnmatch
import os
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import yaml

from beacon.diagnose.kafka.server_config import normalize_bootstrap_servers

SUPPORTED_AUTH_TYPES = {
    "plaintext",
    "mtls",
    "ssl",
    "bearer_token",
    "sasl_oauthbearer",
    "sasl_plain",
    "sasl_scram",
}


@dataclass(frozen=True)
class KafkaAuthConfig:
    type: str
    values: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KafkaAccessProfile:
    name: str
    scope: str
    bootstrap_servers: str
    auth: KafkaAuthConfig
    capabilities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    consumer_groups: List[str] = field(default_factory=list)

    def supports(self, capability, topic=None, consumer_group=None):
        if self.capabilities and capability not in self.capabilities:
            return False

        if topic and self.topics:
            if not any(fnmatch.fnmatch(topic, pattern) for pattern in self.topics):
                return False

        if consumer_group and self.consumer_groups:
            if not any(
                fnmatch.fnmatch(consumer_group, pattern) for pattern in self.consumer_groups
            ):
                return False

        if self.scope == "cluster":
            return topic is None and consumer_group is None

        if self.scope == "topic":
            return topic is not None

        if self.scope == "consumer_group":
            return consumer_group is not None

        return self.scope == "all"

    def evidence(self):
        return {
            "name": self.name,
            "scope": self.scope,
            "bootstrap_servers": self.bootstrap_servers,
            "auth_type": self.auth.type,
            "capabilities": self.capabilities,
            "topics": self.topics,
            "consumer_groups": self.consumer_groups,
        }


@dataclass(frozen=True)
class KafkaAccessConfig:
    profiles: List[KafkaAccessProfile]
    errors: List[Dict[str, object]] = field(default_factory=list)

    @property
    def valid(self):
        return not self.errors and bool(self.profiles)

    def profile_for(self, capability, topic=None, consumer_group=None):
        for profile in self.profiles:
            if profile.supports(capability, topic=topic, consumer_group=consumer_group):
                return profile
        return None

    def posture_issues(self, now=None):
        issues = []

        for profile in self.profiles:
            issues.extend(assess_profile_posture(profile, now=now))

        return issues


def load_kafka_access_config(path):
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as error:
        return KafkaAccessConfig(
            profiles=[],
            errors=[
                {
                    "field": "access_config",
                    "reason": "load_failed",
                    "message": str(error),
                }
            ],
        )

    access = data.get("kafka_access", data)
    profile_configs = access.get("profiles", [])
    profiles = []
    errors = []

    if not isinstance(profile_configs, list) or not profile_configs:
        errors.append(
            {
                "field": "profiles",
                "reason": "missing",
                "message": "kafka_access.profiles must contain at least one profile.",
            }
        )
        return KafkaAccessConfig(profiles=[], errors=errors)

    for index, profile_config in enumerate(profile_configs):
        profile, profile_errors = parse_profile(profile_config, index)
        errors.extend(profile_errors)
        if profile:
            profiles.append(profile)

    return KafkaAccessConfig(profiles=profiles, errors=errors)


def parse_profile(profile_config, index):
    errors = []

    if not isinstance(profile_config, dict):
        return None, [
            {
                "field": f"profiles[{index}]",
                "reason": "invalid_type",
                "message": "Kafka access profile must be a mapping.",
            }
        ]

    name = profile_config.get("name") or f"profile-{index}"
    scope = profile_config.get("scope", "all")
    bootstrap_servers = normalize_bootstrap_servers(
        profile_config.get("bootstrap_servers", profile_config.get("bootstrap_server"))
    )
    auth_config = profile_config.get("auth", {}) or {}
    auth_type = auth_config.get("type", "plaintext")

    if scope not in {"cluster", "topic", "consumer_group", "all"}:
        errors.append(
            {
                "field": f"profiles[{index}].scope",
                "reason": "unsupported",
                "value": scope,
                "message": "Unsupported Kafka access profile scope.",
            }
        )

    if not bootstrap_servers:
        errors.append(
            {
                "field": f"profiles[{index}].bootstrap_servers",
                "reason": "missing",
                "message": "Kafka access profile requires bootstrap_servers.",
            }
        )

    if auth_type not in SUPPORTED_AUTH_TYPES:
        errors.append(
            {
                "field": f"profiles[{index}].auth.type",
                "reason": "unsupported",
                "value": auth_type,
                "supported_values": sorted(SUPPORTED_AUTH_TYPES),
            }
        )

    auth_values = {
        key: resolve_secret_reference(value) for key, value in auth_config.items() if key != "type"
    }

    secret_errors = validate_auth_values(auth_type, auth_values, index)
    errors.extend(secret_errors)

    if errors:
        return None, errors

    return (
        KafkaAccessProfile(
            name=name,
            scope=scope,
            bootstrap_servers=bootstrap_servers,
            auth=KafkaAuthConfig(type=auth_type, values=auth_values),
            capabilities=profile_config.get("capabilities", []) or [],
            topics=profile_config.get("topics", []) or [],
            consumer_groups=profile_config.get("consumer_groups", []) or [],
        ),
        [],
    )


def resolve_secret_reference(value):
    if not isinstance(value, str):
        return value

    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1])

    return value


def validate_auth_values(auth_type, values, index):
    errors = []

    if auth_type in {"bearer_token", "sasl_oauthbearer"}:
        token = values.get("token") or env_value(values.get("token_env"))
        if not token:
            errors.append(
                {
                    "field": f"profiles[{index}].auth.token",
                    "reason": "missing",
                    "message": "Bearer token auth requires token or token_env.",
                }
            )

    if auth_type == "mtls":
        for field_name in ("ca_cert", "client_cert", "client_key"):
            path = values.get(field_name)
            if not path:
                errors.append(
                    {
                        "field": f"profiles[{index}].auth.{field_name}",
                        "reason": "missing",
                        "message": f"mTLS auth requires {field_name}.",
                    }
                )
            elif not os.path.exists(path):
                errors.append(
                    {
                        "field": f"profiles[{index}].auth.{field_name}",
                        "reason": "file_missing",
                        "value": path,
                    }
                )

    if auth_type in {"sasl_plain", "sasl_scram"}:
        if not (values.get("username") or env_value(values.get("username_env"))):
            errors.append(
                {
                    "field": f"profiles[{index}].auth.username",
                    "reason": "missing",
                }
            )
        if not (values.get("password") or env_value(values.get("password_env"))):
            errors.append(
                {
                    "field": f"profiles[{index}].auth.password",
                    "reason": "missing",
                }
            )

    return errors


def assess_profile_posture(profile, now=None):
    issues = []
    auth_type = profile.auth.type
    values = profile.auth.values
    security_protocol = str(values.get("security_protocol", "")).upper()

    if auth_type == "plaintext":
        issues.append(
            posture_issue(
                "kafka.runtime.access.auth.plaintext",
                "HIGH",
                profile,
                "Kafka access profile uses plaintext authentication",
                "Plaintext Kafka access can expose metadata, credentials, or event data on production networks.",
                "Use SSL, mTLS, or SASL over SSL for production Kafka access profiles.",
            )
        )

    if auth_type in {"sasl_plain", "sasl_scram", "bearer_token", "sasl_oauthbearer"}:
        if security_protocol == "PLAINTEXT" or security_protocol == "SASL_PLAINTEXT":
            issues.append(
                posture_issue(
                    "kafka.runtime.access.auth.sasl_without_ssl",
                    "CRITICAL",
                    profile,
                    "Kafka SASL access profile does not require SSL",
                    "SASL without SSL can expose credentials or tokens in transit.",
                    "Use SASL_SSL for production Kafka access profiles.",
                    {"security_protocol": security_protocol},
                )
            )

    if auth_type == "sasl_plain":
        issues.append(
            posture_issue(
                "kafka.runtime.access.auth.sasl_plain",
                "MEDIUM",
                profile,
                "Kafka access profile uses SASL/PLAIN",
                "SASL/PLAIN depends heavily on TLS and secret handling discipline.",
                "Prefer SCRAM, OAUTHBEARER, or mTLS where available; ensure SASL/PLAIN only runs over SSL.",
            )
        )

    if auth_type == "sasl_scram":
        mechanism = values.get("mechanism", "SCRAM-SHA-512")
        if mechanism == "SCRAM-SHA-256":
            issues.append(
                posture_issue(
                    "kafka.runtime.access.auth.scram_sha256",
                    "LOW",
                    profile,
                    "Kafka access profile uses SCRAM-SHA-256",
                    "SCRAM-SHA-256 may be acceptable but is weaker than SCRAM-SHA-512.",
                    "Prefer SCRAM-SHA-512 when supported by the Kafka platform.",
                    {"mechanism": mechanism},
                )
            )

    if profile.scope == "all" and not profile.topics and not profile.consumer_groups:
        issues.append(
            posture_issue(
                "kafka.runtime.access.scope.broad",
                "MEDIUM",
                profile,
                "Kafka access profile has broad all-cluster scope",
                "Broad profiles increase credential blast radius if leaked or overused.",
                "Prefer cluster, topic, or consumer_group scoped profiles with explicit capabilities.",
            )
        )

    if profile.scope == "topic" and not profile.topics:
        issues.append(
            posture_issue(
                "kafka.runtime.access.scope.topic_unbounded",
                "HIGH",
                profile,
                "Kafka topic access profile has no topic patterns",
                "A topic-scoped profile without topic patterns can match every topic.",
                "Set explicit topic names or patterns for topic-scoped profiles.",
            )
        )

    if profile.scope == "consumer_group" and not profile.consumer_groups:
        issues.append(
            posture_issue(
                "kafka.runtime.access.scope.consumer_group_unbounded",
                "MEDIUM",
                profile,
                "Kafka consumer group access profile has no group patterns",
                "A consumer-group-scoped profile without group patterns can match every consumer group.",
                "Set explicit consumer group names or patterns for consumer-group-scoped profiles.",
            )
        )

    for cert_field in ("client_cert", "ca_cert"):
        cert_path = values.get(cert_field)
        expiry_issue = certificate_expiry_issue(profile, cert_field, cert_path, now=now)
        if expiry_issue:
            issues.append(expiry_issue)

    return issues


def posture_issue(rule_id, severity, profile, title, impact, recommendation, extra=None):
    evidence = {"profile": profile.evidence()}
    if extra:
        evidence.update(extra)

    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "evidence": evidence,
    }


def certificate_expiry_issue(profile, cert_field, cert_path, now=None):
    if not cert_path or not os.path.exists(cert_path):
        return None

    try:
        decoded = ssl._ssl._test_decode_cert(cert_path)
    except Exception:
        return None

    not_after = decoded.get("notAfter")
    if not not_after:
        return None

    expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    days_remaining = (expires_at - now).days

    if days_remaining < 0:
        severity = "CRITICAL"
        rule_id = "kafka.runtime.access.cert.expired"
        title = f"Kafka access profile certificate is expired: {cert_field}"
        impact = "Expired Kafka certificates can block diagnostics or production client access."
        recommendation = "Rotate the expired Kafka certificate immediately."
    elif days_remaining <= 30:
        severity = "HIGH"
        rule_id = "kafka.runtime.access.cert.expiring_soon"
        title = f"Kafka access profile certificate expires soon: {cert_field}"
        impact = "Soon-to-expire Kafka certificates can cause unexpected access loss."
        recommendation = "Rotate the Kafka certificate before the expiry window closes."
    else:
        return None

    return posture_issue(
        rule_id,
        severity,
        profile,
        title,
        impact,
        recommendation,
        {
            "cert_field": cert_field,
            "cert_path": cert_path,
            "expires_at": expires_at.isoformat(),
            "days_remaining": days_remaining,
        },
    )


def env_value(name):
    if not name:
        return None
    return os.environ.get(name)


def admin_config_from_profile(profile):
    auth = profile.auth
    values = auth.values

    config = {
        "bootstrap.servers": normalize_bootstrap_servers(profile.bootstrap_servers),
        "socket.timeout.ms": 3000,
        "request.timeout.ms": 3000,
        "metadata.max.age.ms": 30000,
    }

    if auth.type == "plaintext":
        config["security.protocol"] = "PLAINTEXT"
    elif auth.type in {"ssl", "mtls"}:
        config["security.protocol"] = "SSL"
        add_ssl_config(config, values)
    elif auth.type in {"bearer_token", "sasl_oauthbearer"}:
        config["security.protocol"] = values.get("security_protocol", "SASL_SSL")
        config["sasl.mechanisms"] = "OAUTHBEARER"
        token = values.get("token") or env_value(values.get("token_env"))
        if token:
            config["sasl.oauthbearer.config"] = f"token={token}"
        add_ssl_config(config, values)
    elif auth.type == "sasl_plain":
        config["security.protocol"] = values.get("security_protocol", "SASL_SSL")
        config["sasl.mechanisms"] = "PLAIN"
        config["sasl.username"] = values.get("username") or env_value(values.get("username_env"))
        config["sasl.password"] = values.get("password") or env_value(values.get("password_env"))
        add_ssl_config(config, values)
    elif auth.type == "sasl_scram":
        config["security.protocol"] = values.get("security_protocol", "SASL_SSL")
        config["sasl.mechanisms"] = values.get("mechanism", "SCRAM-SHA-512")
        config["sasl.username"] = values.get("username") or env_value(values.get("username_env"))
        config["sasl.password"] = values.get("password") or env_value(values.get("password_env"))
        add_ssl_config(config, values)

    return config


def add_ssl_config(config, values):
    if values.get("ca_cert"):
        config["ssl.ca.location"] = values["ca_cert"]
    if values.get("client_cert"):
        config["ssl.certificate.location"] = values["client_cert"]
    if values.get("client_key"):
        config["ssl.key.location"] = values["client_key"]
