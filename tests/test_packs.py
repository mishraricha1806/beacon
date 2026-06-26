from beacon.packs import get_pack, list_packs, pack_rules_with_metadata, validate_pack


def test_kafka_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("kafka-production-readiness")

    assert pack is not None
    assert pack["name"] == "Kafka Production Readiness"
    assert "Replacing OPA" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 50
    assert validation["missing_metadata"] == []


def test_kubernetes_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("kubernetes-production-readiness")

    assert pack is not None
    assert pack["name"] == "Kubernetes Production Readiness"
    assert "Replacing OPA" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 20
    assert validation["missing_metadata"] == []


def test_terraform_aws_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("terraform-aws-readiness")

    assert pack is not None
    assert pack["name"] == "Terraform AWS Readiness"
    assert "Replacing Terraform" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 20
    assert validation["missing_metadata"] == []


def test_iac_coverage_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("iac-coverage-readiness")

    assert pack is not None
    assert pack["name"] == "IaC Coverage Readiness"
    assert "Automatically importing" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] == 5
    assert validation["missing_metadata"] == []


def test_kafka_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("kafka-production-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert "schema_registry.compatibility.global_unsafe" in rule_ids
    assert "kafka.consumer.security.hostname_verification.disabled" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_kubernetes_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("kubernetes-production-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "k8s.workload.probes.missing" in rule_ids
    assert "k8s.namespace.pod_security.enforce_missing" in rule_ids
    assert "k8s.rbac.cluster_admin.broad_binding" in rule_ids
    assert "k8s.runtime.deployment.unavailable" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_terraform_aws_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("terraform-aws-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "cloud.database.rds.publicly_accessible" in rule_ids
    assert "cloud.database.rds.deletion_protection.disabled" in rule_ids
    assert "iam.managed_admin_policy.attached" in rule_ids
    assert "object_storage.recovery_controls.missing" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_iac_coverage_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("iac-coverage-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "iac_coverage.resource.public_unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_pack_catalog_lists_readiness_packs():
    packs = list_packs()

    assert "kafka-production-readiness" in packs
    assert packs["kafka-production-readiness"]["status"] == "preview"
    assert "kubernetes-production-readiness" in packs
    assert packs["kubernetes-production-readiness"]["status"] == "preview"
    assert "terraform-aws-readiness" in packs
    assert packs["terraform-aws-readiness"]["status"] == "preview"
    assert "iac-coverage-readiness" in packs
    assert packs["iac-coverage-readiness"]["status"] == "preview"
