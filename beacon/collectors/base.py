from abc import ABC, abstractmethod
from typing import Any, Dict


class Collector(ABC):
    """Abstract collector interface.

    A collector gathers signals from a specific domain (Kafka, Kubernetes, cloud, Prometheus)
    and returns a normalized payload (dict) suitable for analyzers.
    """

    @abstractmethod
    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect signals based on the provided configuration.

        Args:
            config: domain-specific connection/configuration parameters.

        Returns:
            Normalized dictionary of collected signals.
        """
        raise NotImplementedError()


class KafkaCollector(Collector):
    """Minimal Kafka collector skeleton.

    This is a thin adapter that will call into the existing runtime connector
    (or a refactored module) and return a normalized dict payload. The goal is
    to separate collection from analysis and make testing easier.

    Implementation note: this skeleton intentionally keeps implementation light
    — the real implementation should handle retries, timeouts, authentication,
    pagination, and graceful degradation.
    """

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Example expected config keys: bootstrap_server, security_protocol, ca_cert, client_cert, client_key, max_topics
        from beacon.kafka_runtime_connector import analyze_kafka_cluster

        findings = analyze_kafka_cluster(
            bootstrap_server=config.get("bootstrap_server"),
            security_protocol=config.get("security_protocol", "PLAINTEXT"),
            ca_cert=config.get("ca_cert"),
            client_cert=config.get("client_cert"),
            client_key=config.get("client_key"),
            max_topics=config.get("max_topics", 50),
            topic=config.get("topic"),
            consumer_group=config.get("consumer_group"),
            max_groups=config.get("max_groups", 20),
        )

        # Return the raw findings for now; analyzers can consume this payload.
        return {"findings": findings}
