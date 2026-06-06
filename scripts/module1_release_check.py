#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import beacon.rules.api_runtime_registered_rules  # noqa: F401
import beacon.rules.cicd_registered_rules  # noqa: F401
import beacon.rules.cloud_registered_rules  # noqa: F401
import beacon.rules.database_runtime_registered_rules  # noqa: F401
import beacon.rules.flow_registered_rules  # noqa: F401
import beacon.rules.iam_registered_rules  # noqa: F401
import beacon.rules.kafka_registered_rules  # noqa: F401
import beacon.rules.kubernetes_registered_rules  # noqa: F401
import beacon.rules.kubernetes_runtime_registered_rules  # noqa: F401
import beacon.rules.storage_registered_rules  # noqa: F401
import beacon.rules.storage_runtime_registered_rules  # noqa: F401
import beacon.rules.topology_registered_rules  # noqa: F401
import beacon.prometheus_connector as prometheus_connector
import beacon.schema_registry_connector as schema_registry_connector
from beacon.engine.registry import registry
from beacon.opentelemetry_connector import analyze_opentelemetry_file
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.engine.metadata_registry import list_rules
from beacon.runtime_snapshot import analyze_runtime_snapshot_file
from beacon.scanner import scan_path


SUPPORTED = ROOT / "examples" / "supported"


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_metadata():
    metadata = list_rules()
    registered = {rule.rule_id for rule in registry.get_all()}
    curated = set()
    for path in (ROOT / "beacon" / "rules" / "metadata").glob("*.yaml"):
        try:
            import yaml

            data = yaml.safe_load(path.read_text()) or {}
        except Exception:
            data = {}
        if isinstance(data, dict) and data.get("rule_id"):
            curated.add(data["rule_id"])
    required = {
        "severity_default",
        "category",
        "title",
        "description",
        "recommendation",
    }

    missing_metadata = sorted(registered - set(metadata))
    missing_curated = sorted(registered - curated)
    missing_required = {
        rule_id: sorted(required - set(data))
        for rule_id, data in metadata.items()
        if required - set(data)
    }

    require(not missing_metadata, f"registered rules missing metadata: {missing_metadata}")
    require(
        not missing_curated,
        f"registered rules missing curated YAML metadata: {missing_curated}",
    )
    require(
        not missing_required,
        f"metadata entries missing required fields: {missing_required}",
    )

    print(f"metadata ok: registered={len(registered)} metadata={len(metadata)}")


def check_static_examples(require_helm):
    expected_by_surface = {
        "terraform": {
            "object_storage.public_access.enabled",
            "cloud.database.rds.publicly_accessible",
            "cloud.compute.ec2.detailed_monitoring.disabled",
        },
        "kafka": {
            "kafka.topic.replication_factor.low",
            "kafka.broker.default_replication_factor.low",
        },
        "kubernetes": {
            "k8s.container.privileged",
            "k8s.runtime.node.not_ready",
        },
        "cicd": {
            "cicd.deployment.environment.missing",
            "cicd.github.permissions.write_all",
        },
        "cloud": {
            "cloud.network.security_group.open_ingress",
            "cloud.database.rds.backup_retention_missing",
        },
        "topology": {
            "topology.service.blast_radius.high",
            "topology.service.critical_single_instance",
        },
    }

    for surface, expected in expected_by_surface.items():
        findings = scan_path(str(SUPPORTED / surface))
        ids = rule_ids(findings)
        require(
            expected <= ids,
            f"{surface} missing expected findings: {sorted(expected - ids)}",
        )

    helm_findings = scan_path(str(SUPPORTED / "helm"))
    helm_ids = rule_ids(helm_findings)
    helm_available = shutil.which("helm") is not None

    if require_helm:
        require(helm_available, "helm CLI is required for release CI")

    if helm_available:
        require(
            "helm.render.unavailable" not in helm_ids,
            "helm was installed but reported unavailable",
        )
        require(
            "helm.render.failed" not in helm_ids,
            "supported Helm chart failed to render",
        )
        require(
            "k8s.workload.replicas.single" in helm_ids,
            "rendered Helm chart was not scanned as Kubernetes",
        )
    else:
        require(
            "helm.render.unavailable" in helm_ids,
            "missing helm should block Helm analysis",
        )

    print("static examples ok")


def check_runtime_snapshot():
    findings = analyze_runtime_snapshot_file(str(SUPPORTED / "runtime" / "all-runtime.yaml"))
    ids = rule_ids(findings)
    expected = {
        "flow.runtime.cascading_latency",
        "api.runtime.retry_amplification",
        "database.runtime.connection_pool.exhaustion",
        "storage.runtime.backup_stale",
    }
    require(
        expected <= ids,
        f"runtime snapshot missing expected findings: {sorted(expected - ids)}",
    )

    summary = calculate_readiness(findings)
    require(
        summary["root_cause_hypotheses"],
        "runtime snapshot produced no root-cause hypotheses",
    )

    top = summary["root_cause_hypotheses"][0]
    require(top["confidence"] in {"MEDIUM", "HIGH"}, "top root-cause confidence is too weak")
    require(top["matched_rule_ids"], "top root-cause hypothesis has no matched rule ids")

    print("runtime snapshot ok")


def check_opentelemetry():
    findings = analyze_opentelemetry_file(str(SUPPORTED / "opentelemetry" / "checkout-otel.yaml"))
    ids = rule_ids(findings)
    expected = {
        "opentelemetry.runtime.read_only_mode",
        "flow.runtime.cascading_latency",
        "database.runtime.connection_pool.exhaustion",
    }
    require(
        expected <= ids,
        f"OpenTelemetry missing expected findings: {sorted(expected - ids)}",
    )

    summary = calculate_readiness(findings)
    require(
        summary["root_cause_hypotheses"],
        "OpenTelemetry produced no root-cause hypotheses",
    )

    print("opentelemetry ok")


def check_prometheus_failure_contract():
    original_query = prometheus_connector.query_prometheus

    def fail_query(*args, **kwargs):
        raise RuntimeError("prometheus unavailable")

    prometheus_connector.query_prometheus = fail_query
    try:
        findings = prometheus_connector.analyze_prometheus_config(
            str(SUPPORTED / "prometheus" / "platform-prometheus.yaml"),
            timeout=1,
        )
    finally:
        prometheus_connector.query_prometheus = original_query

    summary = calculate_readiness(findings)
    require(
        "prometheus.query.failed" in rule_ids(findings),
        "Prometheus failure was not surfaced",
    )
    require(
        summary["score_status"] == "BLOCKED_BY_ANALYSIS_ERROR",
        "Prometheus failure did not block score",
    )
    require(
        summary["production_decision"] == "NOT READY",
        "Prometheus failure did not block readiness",
    )

    print("prometheus failure contract ok")


def check_schema_registry_failure_contract():
    original_query = schema_registry_connector.query_schema_registry

    def fail_query(*args, **kwargs):
        raise RuntimeError("schema registry unavailable")

    schema_registry_connector.query_schema_registry = fail_query
    try:
        findings = schema_registry_connector.analyze_schema_registry_config(
            str(SUPPORTED / "kafka" / "schema-registry.yaml"),
            timeout=1,
        )
    finally:
        schema_registry_connector.query_schema_registry = original_query

    summary = calculate_readiness(findings)
    require(
        "schema_registry.query.failed" in rule_ids(findings),
        "Schema Registry failure was not surfaced",
    )
    require(
        summary["score_status"] == "BLOCKED_BY_ANALYSIS_ERROR",
        "Schema Registry failure did not block score",
    )
    require(
        summary["production_decision"] == "NOT READY",
        "Schema Registry failure did not block readiness",
    )

    print("schema registry failure contract ok")


def main():
    parser = argparse.ArgumentParser(description="Run Beacon Module 1 release checks.")
    parser.add_argument(
        "--require-helm",
        action="store_true",
        help="Fail if Helm is not installed. Use this in release CI.",
    )
    args = parser.parse_args()

    try:
        check_metadata()
        check_static_examples(args.require_helm)
        check_runtime_snapshot()
        check_opentelemetry()
        check_prometheus_failure_contract()
        check_schema_registry_failure_contract()
    except AssertionError as error:
        return fail(str(error))

    print("Module 1 release checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
