#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.html_report import generate_html_report


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def finding(rule_id, domain, severity="HIGH", title=None, evidence=None):
    return {
        "rule_id": rule_id,
        "domain": domain,
        "category": "runtime_stability",
        "severity": severity,
        "title": title or rule_id,
        "impact": "Runtime signal detected.",
        "recommendation": "Investigate the matched runtime signal.",
        "file": "module2-check.yaml",
        "evidence": evidence or {},
        "tags": [],
    }


def playbook_ids(summary):
    return {playbook["id"] for playbook in summary.get("diagnostic_playbooks", [])}


def check_kafka_lag_does_not_invent_db_bottleneck():
    summary = build_diagnostic_summary(
        [
            finding(
                "kafka.consumer_group.lag.high",
                "kafka",
                evidence={"consumer_group": "checkout-consumer", "lag": 10000},
            )
        ]
    )

    hypotheses = summary.get("root_cause_hypotheses", [])
    require(
        all(
            hypothesis["correlation_id"]
            != "correlation.root_cause.downstream_database_bottleneck"
            for hypothesis in hypotheses
        ),
        "Kafka lag alone incorrectly produced a downstream database hypothesis",
    )
    require(
        "module2.kafka.consumer_lag" in playbook_ids(summary),
        "Kafka lag playbook was not matched",
    )
    require(
        any("Kafka lag needs downstream" in gap for gap in summary["telemetry_gaps"]),
        "Kafka lag-only diagnosis did not report downstream telemetry gap",
    )

    print("kafka lag evidence guardrail ok")


def check_flow_db_ranks_database_bottleneck():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.downstream_db_bottleneck",
                "flow",
                evidence={"flow": "checkout", "db_latency_ms": 850},
            ),
            finding(
                "database.runtime.connection_pool.exhaustion",
                "database",
                evidence={"pool_usage_percent": 98},
            ),
        ]
    )

    require(
        summary["primary_hypothesis"]["correlation_id"]
        == "correlation.root_cause.downstream_database_bottleneck",
        "Flow + database evidence did not rank downstream database bottleneck first",
    )
    require(
        "module3.flow.bottleneck" in playbook_ids(summary),
        "Flow bottleneck playbook was not matched",
    )

    print("flow database bottleneck ranking ok")


def check_retry_cascade_beats_generic_storage():
    summary = build_diagnostic_summary(
        [
            finding("flow.runtime.cascading_latency", "flow", severity="CRITICAL"),
            finding("api.runtime.retry_amplification", "api"),
            finding("api.runtime.timeout_rate.high", "api"),
            finding("storage.runtime.capacity.high", "storage"),
        ]
    )

    require(
        summary["primary_hypothesis"]["correlation_id"]
        == "correlation.root_cause.retry_cascade",
        "Retry cascade did not outrank generic storage pressure",
    )
    require(
        "module3.flow.cascading_latency" in playbook_ids(summary),
        "Cascading latency playbook was not matched",
    )

    print("retry cascade ranking ok")


def check_operational_playbook_coverage():
    summary = build_diagnostic_summary(
        [
            finding("kafka.runtime.controller_churn.high", "kafka"),
            finding("kafka.runtime.replay.time_exceeds_target", "kafka"),
            finding("schema_registry.compatibility.global_unsafe", "kafka"),
            finding("kafka.runtime.producer_throttle.high", "kafka"),
            finding("k8s.runtime.pod.crash_loop", "kubernetes"),
            finding("storage.runtime.iops_saturation.high", "storage"),
        ]
    )
    expected = {
        "module2.kafka.cluster_health",
        "module2.kafka.replay_survivability",
        "module2.kafka.schema_poison_message",
        "module2.kafka.auth_quota_throttling",
        "module2.kubernetes.workload_instability",
        "module2.platform.capacity_pressure",
    }

    require(
        expected <= playbook_ids(summary),
        f"missing diagnostic playbooks: {sorted(expected - playbook_ids(summary))}",
    )

    print("operational playbook coverage ok")


def check_cli_json_contract():
    command = [
        sys.executable,
        "-m",
        "beacon.cli",
        "diagnose",
        "flow",
        "examples/supported/runtime/flow-runtime.yaml",
        "--no-html",
        "--no-open-report",
        "--output",
        "json",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    require(
        payload["readiness_summary"] is None,
        "diagnose JSON output should not include a readiness summary",
    )
    require(
        payload["diagnostic_summary"]["diagnostic_playbooks"],
        "diagnose JSON output did not include diagnostic playbooks",
    )
    require(
        payload["diagnostic_summary"]["primary_hypothesis"],
        "diagnose JSON output did not include a primary hypothesis",
    )

    print("diagnose JSON contract ok")


def check_html_contract():
    findings = [
        finding("flow.runtime.cascading_latency", "flow", severity="CRITICAL"),
        finding("api.runtime.retry_amplification", "api"),
    ]
    summary = build_diagnostic_summary(findings)
    generate_html_report(
        findings,
        score=0,
        open_report=False,
        diagnostic_summary=summary,
    )

    report_path = ROOT / "reports" / "report.html"
    html = report_path.read_text()
    require("Runtime Diagnosis" in html, "HTML report missing Runtime Diagnosis")
    require(
        "Matched Diagnostic Playbooks" in html,
        "HTML report missing diagnostic playbooks",
    )

    print("diagnose HTML contract ok")


def main():
    try:
        check_kafka_lag_does_not_invent_db_bottleneck()
        check_flow_db_ranks_database_bottleneck()
        check_retry_cascade_beats_generic_storage()
        check_operational_playbook_coverage()
        check_cli_json_contract()
        check_html_contract()
    except AssertionError as error:
        return fail(str(error))

    print("Module 2 diagnostic checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
