from beacon.packs import get_pack, list_packs, pack_rules_with_metadata, validate_pack


def test_kafka_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("kafka-production-readiness")

    assert pack is not None
    assert pack["name"] == "Kafka Production Readiness"
    assert "Replacing OPA" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 50
    assert validation["missing_metadata"] == []


def test_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("kafka-production-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert "schema_registry.compatibility.global_unsafe" in rule_ids
    assert "kafka.consumer.security.hostname_verification.disabled" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_pack_catalog_lists_kafka_readiness_pack():
    packs = list_packs()

    assert "kafka-production-readiness" in packs
    assert packs["kafka-production-readiness"]["status"] == "preview"
