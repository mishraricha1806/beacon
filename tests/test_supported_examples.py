from pathlib import Path


ROOT = Path("examples/supported")


def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def test_supported_examples_cover_static_surfaces():
    from beacon.scanner import scan_path

    findings = scan_path(str(ROOT / "terraform"))
    ids = rule_ids(findings)

    assert "object_storage.public_access.enabled" in ids
    assert "cloud.database.rds.publicly_accessible" in ids
    assert "cloud.compute.ec2.detailed_monitoring.disabled" in ids

    findings = scan_path(str(ROOT / "kafka"))
    ids = rule_ids(findings)

    assert "kafka.topic.replication_factor.low" in ids
    assert "kafka.broker.default_replication_factor.low" in ids

    findings = scan_path(str(ROOT / "kubernetes"))
    ids = rule_ids(findings)

    assert "k8s.container.privileged" in ids
    assert "k8s.runtime.node.not_ready" in ids


def test_supported_examples_cover_governance_and_topology():
    from beacon.scanner import scan_path

    findings = scan_path(str(ROOT / "cicd"))
    ids = rule_ids(findings)

    assert "cicd.deployment.environment.missing" in ids
    assert "cicd.github.permissions.write_all" in ids

    findings = scan_path(str(ROOT / "cloud"))
    ids = rule_ids(findings)

    assert "cloud.network.security_group.open_ingress" in ids
    assert "cloud.database.rds.backup_retention_missing" in ids

    findings = scan_path(str(ROOT / "topology"))
    ids = rule_ids(findings)

    assert "topology.service.blast_radius.high" in ids
    assert "topology.service.critical_single_instance" in ids


def test_supported_examples_cover_runtime_snapshots():
    from beacon.scanner import scan_file

    findings = scan_file(str(ROOT / "runtime" / "all-runtime.yaml"))
    ids = rule_ids(findings)

    assert "k8s.runtime.node.not_ready" in ids
    assert "flow.runtime.cascading_latency" in ids
    assert "api.runtime.retry_amplification" in ids
    assert "database.runtime.connection_pool.exhaustion" in ids
    assert "storage.runtime.backup_stale" in ids


def test_supported_examples_cover_opentelemetry_export():
    from beacon.opentelemetry_connector import analyze_opentelemetry_file

    findings = analyze_opentelemetry_file(
        str(ROOT / "opentelemetry" / "checkout-otel.yaml")
    )
    ids = rule_ids(findings)

    assert "opentelemetry.runtime.read_only_mode" in ids
    assert "api.runtime.retry_amplification" in ids
    assert "flow.runtime.cascading_latency" in ids
    assert "database.runtime.connection_pool.exhaustion" in ids


def test_supported_helm_example_blocks_without_helm(monkeypatch):
    from beacon import scanner

    monkeypatch.setattr(scanner.shutil, "which", lambda binary: None)

    findings = scanner.scan_path(str(ROOT / "helm"))
    ids = rule_ids(findings)

    assert "helm.render.unavailable" in ids
