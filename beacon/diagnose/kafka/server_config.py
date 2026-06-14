import os
from dataclasses import dataclass
from typing import Dict, List, Optional

SUPPORTED_SECURITY_PROTOCOLS = {"PLAINTEXT", "SSL", "SASL_SSL"}


def normalize_bootstrap_servers(value) -> str:
    if isinstance(value, (list, tuple)):
        parts = [str(item).strip() for item in value]
    else:
        text = str(value or "")
        parts = []
        for line in text.splitlines():
            parts.extend(item.strip() for item in line.split(","))

    return ",".join(part for part in parts if part)


@dataclass(frozen=True)
class KafkaServerConfig:
    bootstrap_server: str
    security_protocol: str = "PLAINTEXT"
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    max_topics: int = 50
    max_groups: int = 20
    topic: Optional[str] = None
    consumer_group: Optional[str] = None

    def evidence(self) -> Dict[str, object]:
        bootstrap_servers = normalize_bootstrap_servers(self.bootstrap_server)
        return {
            "bootstrap_server": bootstrap_servers,
            "bootstrap_servers": bootstrap_servers,
            "bootstrap_server_count": (
                len(bootstrap_servers.split(",")) if bootstrap_servers else 0
            ),
            "security_protocol": self.security_protocol,
            "ca_cert_configured": bool(self.ca_cert),
            "client_cert_configured": bool(self.client_cert),
            "client_key_configured": bool(self.client_key),
            "max_topics": self.max_topics,
            "max_groups": self.max_groups,
            "topic": self.topic,
            "consumer_group": self.consumer_group,
        }

    def validation_errors(self) -> List[Dict[str, object]]:
        errors = []
        bootstrap_servers = normalize_bootstrap_servers(self.bootstrap_server)

        if not bootstrap_servers:
            errors.append(
                {
                    "field": "bootstrap_server",
                    "reason": "missing",
                    "message": "Kafka bootstrap server is required.",
                }
            )

        if self.security_protocol not in SUPPORTED_SECURITY_PROTOCOLS:
            errors.append(
                {
                    "field": "security_protocol",
                    "reason": "unsupported",
                    "value": self.security_protocol,
                    "supported_values": sorted(SUPPORTED_SECURITY_PROTOCOLS),
                    "message": "Unsupported Kafka security protocol.",
                }
            )

        if self.max_topics < 1:
            errors.append(
                {
                    "field": "max_topics",
                    "reason": "invalid_range",
                    "value": self.max_topics,
                    "message": "max_topics must be at least 1.",
                }
            )

        if self.max_groups < 0:
            errors.append(
                {
                    "field": "max_groups",
                    "reason": "invalid_range",
                    "value": self.max_groups,
                    "message": "max_groups cannot be negative.",
                }
            )

        for field, path in {
            "ca_cert": self.ca_cert,
            "client_cert": self.client_cert,
            "client_key": self.client_key,
        }.items():
            if path and not os.path.exists(path):
                errors.append(
                    {
                        "field": field,
                        "reason": "file_missing",
                        "value": path,
                        "message": f"Configured {field} file does not exist.",
                    }
                )

        return errors
