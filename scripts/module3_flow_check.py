#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.flow_runtime import analyze_flow_file


FLOW_SCENARIOS = ROOT / "examples" / "supported" / "flow" / "scenarios"


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def playbook_ids(summary):
    return {playbook["id"] for playbook in summary.get("diagnostic_playbooks", [])}


def primary_correlation(summary):
    primary = summary.get("primary_hypothesis") or {}
    return primary.get("correlation_id")


def check_downstream_database_bottleneck():
    findings = analyze_flow_file(FLOW_SCENARIOS / "downstream-db-bottleneck.yaml")
    ids = rule_ids(findings)
    summary = build_diagnostic_summary(findings)

    require(
        "flow.runtime.downstream_db_bottleneck" in ids,
        "Downstream database bottleneck scenario did not emit flow bottleneck finding",
    )
    require(
        primary_correlation(summary)
        == "correlation.root_cause.downstream_database_bottleneck",
        "Downstream database bottleneck was not the primary root-cause hypothesis",
    )
    require(
        "module3.flow.bottleneck" in playbook_ids(summary),
        "Downstream database bottleneck did not map to Module 3 bottleneck playbook",
    )
    ranking = summary["flow_bottleneck_rankings"][0]
    require(
        ranking["top_bottleneck"] == "database",
        "Downstream database scenario did not rank database as top bottleneck",
    )
    require(
        ranking["top_confidence"] == "HIGH",
        "Downstream database scenario did not produce high-confidence bottleneck ranking",
    )

    print("module3 downstream database bottleneck ok")


def check_deployment_triggered_degradation():
    findings = analyze_flow_file(
        FLOW_SCENARIOS / "deployment-triggered-degradation.yaml"
    )
    ids = rule_ids(findings)
    summary = build_diagnostic_summary(findings)

    require(
        "flow.runtime.deployment_correlated_degradation" in ids,
        "Deployment-triggered scenario did not emit deployment-correlated finding",
    )
    require(
        primary_correlation(summary) == "correlation.root_cause.deployment_regression",
        "Deployment regression was not the primary root-cause hypothesis",
    )
    require(
        "module3.flow.deployment_triggered" in playbook_ids(summary),
        "Deployment-triggered scenario did not map to Module 3 deployment playbook",
    )
    ranking = summary["flow_bottleneck_rankings"][0]
    require(
        ranking["top_bottleneck"] == "api",
        "Deployment-triggered scenario did not rank API as top constrained component",
    )
    require(
        any(
            component["component"] == "deployment"
            for component in ranking["components"]
        ),
        "Deployment-triggered scenario did not retain deployment as causal evidence",
    )

    print("module3 deployment-triggered degradation ok")


def check_cascading_latency():
    findings = analyze_flow_file(FLOW_SCENARIOS / "cascading-latency.yaml")
    ids = rule_ids(findings)
    summary = build_diagnostic_summary(findings)

    require(
        "flow.runtime.cascading_latency" in ids,
        "Cascading latency scenario did not emit cascading latency finding",
    )
    require(
        primary_correlation(summary) == "correlation.root_cause.retry_cascade",
        "Retry cascade was not the primary root-cause hypothesis",
    )
    require(
        "module3.flow.cascading_latency" in playbook_ids(summary),
        "Cascading latency scenario did not map to Module 3 cascading playbook",
    )
    ranking = summary["flow_bottleneck_rankings"][0]
    require(
        ranking["top_bottleneck"] == "api",
        "Cascading latency scenario did not rank API as top bottleneck",
    )

    print("module3 cascading latency ok")


def check_all_domain_flow_diagnostics_json():
    command = [
        sys.executable,
        "-m",
        "beacon.cli",
        "diagnose",
        "all",
        "--snapshot",
        "examples/supported/runtime/all-runtime.yaml",
        "--kafka-history",
        "examples/supported/kafka/history.yaml",
        "--deployment-events",
        "examples/supported/deployments/events.yaml",
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
    summary = payload["diagnostic_summary"]
    playbooks = playbook_ids(summary)

    require(
        primary_correlation(summary) == "correlation.root_cause.deployment_regression",
        "All-domain flow diagnosis did not rank deployment regression first",
    )
    require(
        {
            "module3.flow.bottleneck",
            "module3.flow.deployment_triggered",
            "module3.flow.cascading_latency",
        }
        <= playbooks,
        f"All-domain flow diagnosis missing Module 3 playbooks: {sorted(playbooks)}",
    )
    require(
        summary["flow_bottleneck_rankings"],
        "All-domain flow diagnosis did not include flow bottleneck rankings",
    )

    print("module3 all-domain JSON contract ok")


def main():
    try:
        check_downstream_database_bottleneck()
        check_deployment_triggered_degradation()
        check_cascading_latency()
        check_all_domain_flow_diagnostics_json()
    except AssertionError as error:
        return fail(str(error))

    print("Module 3 flow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
