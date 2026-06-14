# new test file
import sys
import types
import beacon.kafka_runtime_connector as krc

# Create a minimal fake confluent_kafka and confluent_kafka.admin to allow importing the module
fake_ck = types.ModuleType("confluent_kafka")
fake_ck.TopicPartition = type("TopicPartition", (), {})
fake_ck.ConsumerGroupTopicPartitions = type(
    "ConsumerGroupTopicPartitions", (), {"__init__": lambda self, gid: None}
)

fake_admin = types.ModuleType("confluent_kafka.admin")
# Provide placeholders for names imported by the connector
fake_admin.AdminClient = lambda cfg: object()
fake_admin.ConfigResource = lambda *a, **k: None
fake_admin.ResourceType = type("ResourceType", (), {"TOPIC": "topic"})


class _OffsetSpec:
    @staticmethod
    def latest():
        return None


fake_admin.OffsetSpec = _OffsetSpec

# Insert into sys.modules before importing the connector
sys.modules["confluent_kafka"] = fake_ck
sys.modules["confluent_kafka.admin"] = fake_admin


def test_analyze_kafka_cluster_handles_adminclient_failure(monkeypatch):
    # Make AdminClient raise when constructed
    def raise_on_init(cfg):
        raise Exception("simulated connection failure")

    monkeypatch.setattr(krc, "AdminClient", raise_on_init)

    findings = krc.analyze_kafka_cluster(bootstrap_server="invalid:9092")

    assert isinstance(findings, list)
    assert any(
        f.get("severity") == "ERROR" for f in findings
    ), "Expected an ERROR finding when connection fails"
