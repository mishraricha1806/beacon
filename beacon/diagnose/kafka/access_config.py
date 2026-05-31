import fnmatch
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


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
                fnmatch.fnmatch(consumer_group, pattern)
                for pattern in self.consumer_groups
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
    bootstrap_servers = profile_config.get(
        "bootstrap_servers", profile_config.get("bootstrap_server")
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
        key: resolve_secret_reference(value)
        for key, value in auth_config.items()
        if key != "type"
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


def env_value(name):
    if not name:
        return None
    return os.environ.get(name)


def admin_config_from_profile(profile):
    auth = profile.auth
    values = auth.values

    config = {
        "bootstrap.servers": profile.bootstrap_servers,
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
        config["sasl.username"] = values.get("username") or env_value(
            values.get("username_env")
        )
        config["sasl.password"] = values.get("password") or env_value(
            values.get("password_env")
        )
        add_ssl_config(config, values)
    elif auth.type == "sasl_scram":
        config["security.protocol"] = values.get("security_protocol", "SASL_SSL")
        config["sasl.mechanisms"] = values.get("mechanism", "SCRAM-SHA-512")
        config["sasl.username"] = values.get("username") or env_value(
            values.get("username_env")
        )
        config["sasl.password"] = values.get("password") or env_value(
            values.get("password_env")
        )
        add_ssl_config(config, values)

    return config


def add_ssl_config(config, values):
    if values.get("ca_cert"):
        config["ssl.ca.location"] = values["ca_cert"]
    if values.get("client_cert"):
        config["ssl.certificate.location"] = values["client_cert"]
    if values.get("client_key"):
        config["ssl.key.location"] = values["client_key"]
