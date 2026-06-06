# Add test to ensure HTML report renders rule_id and evidence

import os

from beacon.html_report import generate_html_report


def test_generate_html_includes_rule_id_and_evidence(tmp_path):
    findings = [
        {
            "severity": "HIGH",
            "title": "Kafka topic 'payments' has replication factor 1",
            "impact": "impact",
            "recommendation": "Use replication_factor=3",
            "file": "examples/kafka-topics.yaml",
            "rule_id": "kafka.topic.replication_factor.low",
            "evidence": {"path": "topics[0].replication_factor", "value": 1},
        }
    ]

    # Ensure reports output path does not conflict; generate will write reports/report.html
    generate_html_report(findings, score=42, open_report=False, readiness_summary=None)

    out_path = os.path.join("reports", "report.html")
    assert os.path.exists(out_path)

    with open(out_path, "r") as f:
        html = f.read()

    assert "kafka.topic.replication_factor.low" in html
    assert "topics[0].replication_factor" in html


def test_generate_html_includes_release_gate_card():
    readiness_summary = {
        "score": 52,
        "production_decision": "NOT READY",
        "survivability": "CRITICAL RISK",
        "primary_risk_area": "Operational Safety",
        "risk_points": 96,
        "business_summary": "The system has production-readiness gaps.",
        "recommended_action": "Fix critical risks before rollout.",
        "critical": 1,
        "high": 1,
        "medium": 0,
        "low": 0,
        "environment": "prod",
        "intelligence_context": {"loaded": False},
        "score_formula": "weighted severity model",
        "release_gate": {
            "question": "Is this production ready?",
            "answer": "No",
            "decision": "NOT READY",
            "score": 52,
            "why_not": ["CRITICAL: Kafka topic has replication factor 1"],
            "fix_first": ["Fix critical resiliency risks before rollout."],
            "business_risk": "The release can fail during broker loss.",
        },
        "business_categories": {},
        "architect_assessment": None,
        "distributed_system_readiness": None,
        "top_reasons": [],
        "next_best_actions": [],
        "categories": {},
        "kafka_report": None,
        "grouped_risks": [],
    }

    generate_html_report([], score=52, open_report=False, readiness_summary=readiness_summary)

    out_path = os.path.join("reports", "report.html")
    with open(out_path, "r") as f:
        html = f.read()

    assert "Is this production ready?" in html
    assert "Why Not?" in html
    assert "Fix First" in html
    assert "Business Risk" in html


def test_generate_html_includes_flow_bottleneck_ranking():
    diagnostic_summary = {
        "diagnostic_status": "ROOT_CAUSE_CANDIDATES_FOUND",
        "executive_summary": "Beacon found a flow bottleneck.",
        "primary_hypothesis": None,
        "first_actions": [],
        "diagnostic_playbooks": [],
        "consumer_group_diagnoses": [],
        "flow_bottleneck_rankings": [
            {
                "flow": "checkout",
                "top_bottleneck": "database",
                "top_confidence": "HIGH",
                "components": [
                    {
                        "rank": 1,
                        "component": "database",
                        "component_type": "database",
                        "confidence": "HIGH",
                        "status": "likely_bottleneck",
                        "reason": "Database latency is high while Kafka appears healthy.",
                    }
                ],
            }
        ],
        "telemetry_gaps": [],
        "affected_domains": [],
    }

    generate_html_report(
        [],
        score=0,
        open_report=False,
        diagnostic_summary=diagnostic_summary,
    )

    out_path = os.path.join("reports", "report.html")
    with open(out_path, "r") as f:
        html = f.read()

    assert "Flow Bottleneck Ranking" in html
    assert "database" in html


def test_generate_html_includes_deployment_before_after_window():
    diagnostic_summary = {
        "diagnostic_status": "ROOT_CAUSE_CANDIDATES_FOUND",
        "executive_summary": "Beacon found a deployment regression.",
        "primary_hypothesis": None,
        "first_actions": [],
        "diagnostic_playbooks": [],
        "consumer_group_diagnoses": [],
        "flow_bottleneck_rankings": [],
        "deployment_window_analyses": [
            {
                "service": "checkout-api",
                "version": "v1.42.1",
                "deployed_at": "2026-06-03T10:20:00Z",
                "metrics": [
                    {
                        "metric": "api_latency_p95_ms",
                        "before": 220,
                        "after": 1600,
                        "delta": 1380,
                        "ratio": 7.27,
                        "severity": "HIGH",
                    }
                ],
            }
        ],
        "telemetry_gaps": [],
        "affected_domains": [],
    }

    generate_html_report(
        [],
        score=0,
        open_report=False,
        diagnostic_summary=diagnostic_summary,
    )

    with open(os.path.join("reports", "report.html"), "r") as f:
        html = f.read()

    assert "Before / After Deployment" in html
    assert "api_latency_p95_ms" in html
    assert "1600" in html


def test_generate_html_includes_incident_diagnosis_card():
    diagnostic_summary = {
        "diagnostic_status": "DEGRADATION_SIGNALS_FOUND",
        "executive_summary": "Beacon found Kafka instability.",
        "primary_hypothesis": None,
        "incident_diagnosis": {
            "title": "Consumer Group Instability",
            "confidence": "HIGH",
            "summary": "Consumer group checkout-consumer is rebalancing.",
            "recommendation": "Inspect recent consumer deployments.",
            "evidence_quality": {
                "status": "ACTIONABLE",
                "score": 82,
                "reason": "Beacon has multiple deterministic signals.",
            },
            "evidence": [
                "Consumer group: checkout-consumer",
                "Status: REBALANCING",
            ],
            "first_actions": ["Check consumer pod restarts."],
            "missing_evidence": ["deployment timeline"],
            "runbook": {
                "title": "Kafka Consumer Instability Runbook",
                "check_first": ["Check recent consumer deployments."],
                "safe_actions": ["Pause risky rollout."],
                "avoid": ["Do not add partitions first."],
                "evidence_to_collect": ["Consumer restart history"],
            },
        },
        "first_actions": [],
        "diagnostic_playbooks": [],
        "consumer_group_diagnoses": [],
        "flow_bottleneck_rankings": [],
        "deployment_window_analyses": [],
        "telemetry_gaps": [],
        "affected_domains": [],
    }

    generate_html_report(
        [],
        score=0,
        open_report=False,
        diagnostic_summary=diagnostic_summary,
    )

    with open(os.path.join("reports", "report.html"), "r") as f:
        html = f.read()

    assert "Incident Diagnosis" in html
    assert "Primary Likely Cause" in html
    assert "Consumer Group Instability" in html
    assert "Evidence Quality" in html
    assert "ACTIONABLE" in html
    assert "Why Beacon Thinks This" in html
    assert "What To Do First" in html
    assert "Kafka Consumer Instability Runbook" in html
    assert "Do not add partitions first." in html
