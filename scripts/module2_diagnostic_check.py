#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.deployment_events import analyze_deployment_events_file
from beacon.html_report import generate_html_report
from beacon.kafka_history import analyze_kafka_history_file
from beacon.runtime_advisor import analyze_runtime_file
import beacon.prometheus_connector as prometheus_connector


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
            hypothesis["correlation_id"] != "correlation.root_cause.downstream_database_bottleneck"
            for hypothesis in hypotheses
        ),
        "Kafka lag alone incorrectly produced a downstream database hypothesis",
    )
    require(
        "module2.kafka.consumer_lag" in playbook_ids(summary),
        "Kafka lag playbook was not matched",
    )
    require(
        summary["consumer_group_diagnoses"],
        "Kafka lag diagnosis did not include consumer_group_diagnoses",
    )
    diagnosis = summary["consumer_group_diagnoses"][0]
    require(
        diagnosis["consumer_group"] == "checkout-consumer",
        "Kafka lag diagnosis did not preserve the consumer group",
    )
    require(
        diagnosis["primary_likely_cause"] == "lag_requires_more_evidence",
        "Kafka lag-only diagnosis should require more evidence before naming a cause",
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
        summary["primary_hypothesis"]["correlation_id"] == "correlation.root_cause.retry_cascade",
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


def check_kafka_incident_scenario(
    name,
    relative_path,
    expected_rules,
    expected_playbooks,
    expected_incident_title,
):
    findings = analyze_runtime_file(str(ROOT / relative_path))
    rule_ids = {finding["rule_id"] for finding in findings}
    require(
        expected_rules <= rule_ids,
        f"{name} scenario missing findings: {sorted(expected_rules - rule_ids)}",
    )

    summary = build_diagnostic_summary(findings)
    playbooks = playbook_ids(summary)
    require(
        expected_playbooks <= playbooks,
        f"{name} scenario missing playbooks: {sorted(expected_playbooks - playbooks)}",
    )
    require(
        summary["incident_diagnosis"]["title"] == expected_incident_title,
        (f"{name} scenario incident title was " f"{summary['incident_diagnosis']['title']!r}"),
    )

    print(f"kafka incident scenario ok: {name}")


def check_kafka_hot_partition_scenario():
    summary = build_diagnostic_summary(
        [
            finding(
                "kafka.consumer_group.lag.high",
                "kafka",
                evidence={
                    "consumer_group": "checkout-consumer",
                    "total_lag": 120000,
                    "partition_count": 8,
                },
            ),
            finding(
                "kafka.consumer_group.hot_partition",
                "kafka",
                evidence={
                    "consumer_group": "checkout-consumer",
                    "max_partition_lag": 85000,
                    "hot_partitions": [
                        {
                            "topic": "checkout-events",
                            "partition": 3,
                            "lag": 85000,
                        }
                    ],
                    "affected_topics": ["checkout-events"],
                },
            ),
        ]
    )

    require(
        "module2.kafka.partition_skew" in playbook_ids(summary),
        "Hot partition scenario did not map to partition skew playbook",
    )
    require(
        summary["consumer_group_diagnoses"],
        "Hot partition scenario did not produce a consumer group diagnosis",
    )
    require(
        summary["consumer_group_diagnoses"][0]["primary_likely_cause"]
        == "partition_skew_or_hot_key",
        "Hot partition scenario did not rank partition skew as the likely cause",
    )

    print("kafka incident scenario ok: hot partition")


def check_kafka_incident_scenario_pack():
    check_kafka_incident_scenario(
        "rebalance storm",
        Path("examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml"),
        {
            "kafka.runtime.rebalance_storm",
            "kafka.runtime.consumer_group.unstable",
            "kafka.runtime.consumer_group.member_shortfall",
        },
        {"module2.kafka.consumer_instability"},
        "Why are consumers unstable?",
    )
    check_kafka_incident_scenario(
        "quota and throttling",
        Path("examples/supported/kafka/scenarios/quota-throttle-runtime.yaml"),
        {
            "kafka.runtime.producer_error_rate.high",
            "kafka.runtime.producer_throttle.high",
            "kafka.runtime.fetch_throttle.high",
            "kafka.runtime.request_latency.high",
            "kafka.runtime.request_queue_saturation.high",
            "kafka.runtime.network_saturation.high",
        },
        {
            "module2.kafka.auth_quota_throttling",
            "module2.kafka.cluster_health",
        },
        "Are clients failing because of auth, ACLs, quotas, or throttling?",
    )
    check_kafka_incident_scenario(
        "schema poison message",
        Path("examples/supported/kafka/scenarios/schema-poison-runtime.yaml"),
        {
            "kafka.runtime.schema_registry.unavailable",
            "kafka.runtime.schema_incompatible_changes",
        },
        {"module2.kafka.schema_poison_message"},
        "Could schema or poison messages break consumers?",
    )
    check_kafka_hot_partition_scenario()


def check_kafka_history_trend_contract():
    findings = analyze_kafka_history_file("examples/supported/kafka/history.yaml")
    rule_ids = {finding["rule_id"] for finding in findings}
    expected = {
        "kafka.history.consumer_lag.growing",
        "kafka.history.producer_rate.increased",
        "kafka.history.deployment_correlated_lag",
    }
    require(
        expected <= rule_ids,
        f"Kafka history trend contract missing findings: {sorted(expected - rule_ids)}",
    )

    summary = build_diagnostic_summary(findings)
    playbooks = playbook_ids(summary)
    require(
        "module2.kafka.consumer_lag" in playbooks,
        "Kafka history lag trend did not map to consumer lag playbook",
    )
    require(
        "module2.kafka.scale_or_optimize" in playbooks,
        "Kafka producer-rate trend did not map to scale-vs-optimize playbook",
    )

    print("kafka history trend contract ok")


def check_deployment_event_correlation_contract():
    runtime_findings = [
        finding(
            "kafka.consumer_group.lag.high",
            "kafka",
            evidence={"consumer_group": "checkout-consumer", "lag": 10000},
        )
    ]
    deployment_findings = analyze_deployment_events_file(
        ROOT / "examples" / "supported" / "deployments" / "events.yaml",
        existing_findings=runtime_findings,
    )
    rule_ids = {finding["rule_id"] for finding in deployment_findings}

    require(
        "deployment.events.loaded" in rule_ids,
        "Deployment event input was not loaded",
    )
    require(
        "deployment.runtime.degradation_correlated" in rule_ids,
        "Deployment event input did not correlate with runtime degradation",
    )

    summary = build_diagnostic_summary(runtime_findings + deployment_findings)
    require(
        summary["primary_hypothesis"]["correlation_id"]
        == "correlation.root_cause.deployment_regression",
        "Deployment correlation did not rank deployment regression first",
    )
    require(
        "module3.flow.deployment_triggered" in playbook_ids(summary),
        "Deployment correlation did not map to deployment-triggered playbook",
    )

    print("deployment event correlation contract ok")


def check_prometheus_kafka_jmx_contract():
    values = {
        "log_size_bytes": 88,
        "underminisr": 2,
        "underreplicated": 2,
        "offlinepartitionscount": 1,
        "preferredreplicaimbalancecount": 55,
        "activecontrollercount": 2,
        "leaderelectionrateandtimems": 4,
        "reassigningpartitions": 2,
        "replicafetchermanager_maxlag": 15000,
        "failedproducerequests": 7,
        "histogram_quantile": 700,
        "requestqueuepercent": 86,
        "bytesin_total": 92,
        'throttle_timems{request="Produce"}': 140,
        'throttle_timems{request=~"FetchConsumer|Fetch"}': 160,
        "schema-registry": 0,
        "incompatible_schema": 1,
        "kafka_consumergroup_lag": 1000000,
        "records_consumed": 100,
        "messagesin_total": 50,
    }

    original_query = prometheus_connector.query_prometheus
    original_map = prometheus_connector.query_prometheus_map

    def fake_query(_base_url, query, timeout=5):
        normalized = query.lower()
        for key, value in values.items():
            if key.lower() in normalized:
                return value
        raise AssertionError(query)

    def fake_map(_base_url, query, label, timeout=5):
        if "log_size_bytes" in query.lower():
            return {"1": 94, "2": 62, "3": 60}
        raise AssertionError(query)

    prometheus_connector.query_prometheus = fake_query
    prometheus_connector.query_prometheus_map = fake_map
    try:
        findings = prometheus_connector.analyze_prometheus_config(
            str(ROOT / "examples" / "supported" / "prometheus" / "kafka-jmx-prometheus.yaml")
        )
    finally:
        prometheus_connector.query_prometheus = original_query
        prometheus_connector.query_prometheus_map = original_map

    rule_ids = {finding["rule_id"] for finding in findings}
    expected = {
        "kafka.runtime.broker_disk_skew.critical",
        "kafka.runtime.under_min_isr_partitions",
        "kafka.runtime.under_replicated_partitions",
        "kafka.runtime.offline_partitions",
        "kafka.runtime.controller_count.invalid",
        "kafka.runtime.controller_churn.high",
        "kafka.runtime.replication_fetcher_lag.high",
        "kafka.runtime.request_latency.high",
        "kafka.runtime.request_queue_saturation.high",
        "kafka.runtime.network_saturation.high",
        "kafka.runtime.producer_throttle.high",
        "kafka.runtime.fetch_throttle.high",
        "kafka.runtime.schema_registry.unavailable",
        "kafka.runtime.schema_incompatible_changes",
        "kafka.runtime.replay.time_exceeds_target",
        "kafka.runtime.replay.retention_window_insufficient",
    }
    require(
        expected <= rule_ids,
        f"Prometheus Kafka JMX contract missing findings: {sorted(expected - rule_ids)}",
    )

    print("prometheus kafka jmx contract ok")


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
        "consumer_group_diagnoses" in payload["diagnostic_summary"],
        "diagnose JSON output did not include consumer_group_diagnoses",
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
        finding(
            "kafka.consumer_group.lag.high",
            "kafka",
            evidence={"consumer_group": "checkout-consumer", "total_lag": 100000},
        ),
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
    require(
        "Kafka Consumer Group Diagnosis" in html,
        "HTML report missing Kafka consumer group diagnosis",
    )

    print("diagnose HTML contract ok")


def main():
    try:
        check_kafka_lag_does_not_invent_db_bottleneck()
        check_flow_db_ranks_database_bottleneck()
        check_retry_cascade_beats_generic_storage()
        check_operational_playbook_coverage()
        check_kafka_incident_scenario_pack()
        check_kafka_history_trend_contract()
        check_deployment_event_correlation_contract()
        check_prometheus_kafka_jmx_contract()
        check_cli_json_contract()
        check_html_contract()
    except AssertionError as error:
        return fail(str(error))

    print("Module 2 diagnostic checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
