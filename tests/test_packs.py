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


def test_cloud_production_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("cloud-production-readiness")

    assert pack is not None
    assert pack["name"] == "Cloud Production Readiness"
    assert "full AWS, Azure, and GCP parity" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 34
    assert validation["missing_metadata"] == []


def test_cloud_azure_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("cloud-azure-readiness")

    assert pack is not None
    assert pack["name"] == "Azure Cloud Readiness"
    assert "complete Azure coverage" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 10
    assert validation["missing_metadata"] == []


def test_cloud_gcp_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("cloud-gcp-readiness")

    assert pack is not None
    assert pack["name"] == "GCP Cloud Readiness"
    assert "complete GCP coverage" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 11
    assert validation["missing_metadata"] == []


def test_iac_coverage_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("iac-coverage-readiness")

    assert pack is not None
    assert pack["name"] == "IaC Coverage Readiness"
    assert "Automatically importing" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] == 5
    assert validation["missing_metadata"] == []


def test_distributed_system_readiness_pack_is_discoverable_and_metadata_backed():
    pack = get_pack("distributed-system-production-readiness")

    assert pack is not None
    assert pack["name"] == "Distributed System Production Readiness"
    assert "Replacing domain-specific packs" in " ".join(pack["non_goals"])

    validation = validate_pack(pack)

    assert validation["rule_count"] >= 40
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


def test_cloud_production_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("cloud-production-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "cloud.network.security_group.open_ingress" in rule_ids
    assert "cloud.database.azure.public_network_access.enabled" in rule_ids
    assert "cloud.key_vault.azure.public_network_access.enabled" in rule_ids
    assert "cloud.network.azure.private_endpoint.missing" in rule_ids
    assert "cloud.compute.azure.vmss.scale_headroom.insufficient" in rule_ids
    assert "cloud.quota.azure.headroom.insufficient" in rule_ids
    assert "cloud.database.gcp.public_ip.enabled" in rule_ids
    assert "cloud.network.gcp.firewall.open_ingress" in rule_ids
    assert "cloud.kubernetes.gcp.private_nodes.disabled" in rule_ids
    assert "cloud.kubernetes.gcp.regional_resiliency.missing" in rule_ids
    assert "cloud.quota.gcp.headroom.insufficient" in rule_ids
    assert "iam.permissions.wildcard" in rule_ids
    assert "object_storage.versioning.missing" in rule_ids
    assert "cloud.quota.headroom.insufficient" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_cloud_azure_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("cloud-azure-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "object_storage.public_access.enabled" in rule_ids
    assert "cloud.database.azure.public_network_access.enabled" in rule_ids
    assert "cloud.database.azure.backup_retention.weak" in rule_ids
    assert "cloud.database.azure.ha.disabled" in rule_ids
    assert "cloud.database.azure.deletion_protection.missing" in rule_ids
    assert "cloud.database.azure.customer_managed_key.missing" in rule_ids
    assert "cloud.key_vault.azure.public_network_access.enabled" in rule_ids
    assert "cloud.key_vault.azure.purge_protection.disabled" in rule_ids
    assert "cloud.network.azure.private_endpoint.missing" in rule_ids
    assert "cloud.compute.azure.vmss.scale_headroom.insufficient" in rule_ids
    assert "cloud.quota.azure.headroom.insufficient" in rule_ids
    assert "object_storage.encryption.missing" in rule_ids
    assert "object_storage.labels_or_tags.missing" in rule_ids
    assert "iam.admin_or_owner.excessive" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_cloud_gcp_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("cloud-gcp-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "object_storage.versioning.missing" in rule_ids
    assert "cloud.database.gcp.public_ip.enabled" in rule_ids
    assert "cloud.database.gcp.backup.disabled" in rule_ids
    assert "cloud.database.gcp.deletion_protection.disabled" in rule_ids
    assert "cloud.database.gcp.ha.disabled" in rule_ids
    assert "cloud.database.gcp.cmek.missing" in rule_ids
    assert "cloud.network.gcp.firewall.open_ingress" in rule_ids
    assert "cloud.kubernetes.gcp.private_nodes.disabled" in rule_ids
    assert "cloud.kubernetes.gcp.master_authorized_networks.missing" in rule_ids
    assert "cloud.kubernetes.gcp.regional_resiliency.missing" in rule_ids
    assert "cloud.quota.gcp.headroom.insufficient" in rule_ids
    assert "object_storage.labels_or_tags.missing" in rule_ids
    assert "gcp.storage.uniform_bucket_access.disabled" in rule_ids
    assert "iam.admin_or_owner.excessive" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_iac_coverage_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("iac-coverage-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "iac_coverage.resource.public_unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_distributed_system_pack_rules_resolve_human_readable_metadata():
    pack = get_pack("distributed-system-production-readiness")
    rows = pack_rules_with_metadata(pack)
    rule_ids = {row["rule_id"] for row in rows}

    assert "kafka.topic.replication_factor.low" in rule_ids
    assert "k8s.workload.probes.missing" in rule_ids
    assert "cloud.database.azure.public_network_access.enabled" in rule_ids
    assert "cloud.network.gcp.firewall.open_ingress" in rule_ids
    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "cicd.github.permissions.write_all" in rule_ids
    assert "topology.service.blast_radius.high" in rule_ids
    assert "readiness.correlation.internet_exposed_database" in rule_ids
    assert "flow.runtime.downstream_db_bottleneck" in rule_ids
    assert all(row["metadata_found"] for row in rows)


def test_pack_catalog_lists_readiness_packs():
    packs = list_packs()

    assert "kafka-production-readiness" in packs
    assert packs["kafka-production-readiness"]["status"] == "preview"
    assert "kubernetes-production-readiness" in packs
    assert packs["kubernetes-production-readiness"]["status"] == "preview"
    assert "cloud-production-readiness" in packs
    assert packs["cloud-production-readiness"]["status"] == "preview"
    assert "cloud-azure-readiness" in packs
    assert packs["cloud-azure-readiness"]["status"] == "preview"
    assert "cloud-gcp-readiness" in packs
    assert packs["cloud-gcp-readiness"]["status"] == "preview"
    assert "terraform-aws-readiness" in packs
    assert packs["terraform-aws-readiness"]["status"] == "preview"
    assert "iac-coverage-readiness" in packs
    assert packs["iac-coverage-readiness"]["status"] == "preview"
    assert "distributed-system-production-readiness" in packs
    assert packs["distributed-system-production-readiness"]["status"] == "preview"
