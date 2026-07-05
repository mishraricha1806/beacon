#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beacon.deployment_events import analyze_deployment_events_file
from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.runtime_advisor import analyze_runtime_file
from beacon.scanner import scan_path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def decision_targets(summary):
    return {decision["target"]: decision for decision in summary.get("operational_decisions", [])}


def check_rollback_before_scale_decision():
    findings = analyze_deployment_events_file(
        ROOT / "examples/supported/module4/rollback-vs-scale-deployment.yaml"
    )
    summary = build_diagnostic_summary(findings, environment="prod")
    decisions = decision_targets(summary)
    decision = decisions.get("rollback_decision")

    require(decision, "rollback-vs-scale example did not produce rollback decision")
    require(
        "before capacity scaling" in decision["action"],
        "rollback decision did not prioritize rollback before scaling",
    )
    require(
        any("scaling infrastructure first" in item for item in decision["do_not_do"]),
        "rollback decision did not include anti-scaling guidance",
    )
    print("module4 rollback-before-scale decision ok")


def check_kafka_client_pressure_decision():
    findings = analyze_runtime_file(
        ROOT / "examples/supported/module4/kafka-client-pressure-runtime.yaml"
    )
    summary = build_diagnostic_summary(findings)
    decisions = decision_targets(summary)
    decision = decisions.get("kafka_client_pressure")

    require(decision, "client-pressure example did not produce Kafka client decision")
    require(
        "throttled or noisy Kafka clients" in decision["action"],
        "Kafka client decision did not call out noisy/throttled clients",
    )
    require(
        any("remove quotas" in item for item in decision["do_not_do"]),
        "Kafka client decision did not warn against removing quotas blindly",
    )
    print("module4 kafka-client-pressure decision ok")


def check_retention_cleanup_decision():
    findings = analyze_runtime_file(
        ROOT / "examples/supported/module4/retention-cleanup-runtime.yaml"
    )
    summary = build_diagnostic_summary(findings)
    decisions = decision_targets(summary)
    decision = decisions.get("kafka_retention_cleanup")

    require(decision, "retention example did not produce retention cleanup decision")
    require(
        "before buying more Kafka storage" in decision["action"],
        "retention decision did not prioritize cleanup before storage expansion",
    )
    require(
        "broker disk time-to-full" in decision["evidence_required"],
        "retention decision did not request time-to-full evidence",
    )
    print("module4 retention-cleanup decision ok")


def check_kubernetes_security_decision():
    findings = scan_path(
        str(ROOT / "examples/supported/module4/kubernetes-security-readiness.yaml")
    )
    summary = calculate_readiness(findings, environment="prod")
    decisions = decision_targets(summary)
    decision = decisions.get("kubernetes_security")

    require(decision, "Kubernetes security example did not produce security decision")
    require(
        "privilege, secret, and network-isolation risks" in decision["action"],
        "Kubernetes security decision did not call out privilege/secret/network risks",
    )
    require(
        any("inline secrets" in item for item in decision["do_not_do"]),
        "Kubernetes security decision did not warn against approving inline secrets",
    )
    require(
        "NetworkPolicy coverage" in decision["evidence_required"],
        "Kubernetes security decision did not request NetworkPolicy evidence",
    )
    print("module4 kubernetes-security decision ok")


def main():
    check_rollback_before_scale_decision()
    check_kafka_client_pressure_decision()
    check_retention_cleanup_decision()
    check_kubernetes_security_decision()
    print("Module 4 decision checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
