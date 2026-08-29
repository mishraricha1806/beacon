# Add test to ensure HTML report renders rule_id and evidence

import os

from beacon.html_report import finding_anchor_id, generate_html_report


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


def test_generate_html_escapes_untrusted_finding_content():
    findings = [
        {
            "severity": "HIGH",
            "title": '<script>alert("beacon")</script>',
            "impact": '<img src=x onerror="alert(1)">',
            "recommendation": "Review the source evidence.",
            "file": "untrusted.yaml",
            "rule_id": "scanner.untrusted.content",
            "evidence": {"value": "<b>not trusted markup</b>"},
        }
    ]

    generate_html_report(findings, score=50, open_report=False)

    with open(os.path.join("reports", "report.html"), "r") as report_file:
        html = report_file.read()

    assert '<script>alert("beacon")</script>' not in html
    assert "&lt;script&gt;" in html
    assert '<img src=x onerror="alert(1)">' not in html
    assert "&lt;img src=x" in html


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
        "release_evidence": {
            "production_blockers": {
                "question": "What blocks production?",
                "status": "Production is blocked",
                "decision": "NOT READY",
                "score": 52,
                "blockers": [
                    {
                        "severity": "CRITICAL",
                        "title": "Kafka topics have replication factor 1",
                        "affected_count": 1,
                    }
                ],
                "fix_first": ["Fix Kafka replication before rollout."],
                "business_impact": "The release can fail during broker loss.",
            }
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
    assert "What blocks production?" in html
    assert "Kafka topics have replication factor 1" in html
    assert "Fix Kafka replication before rollout." in html


def test_generate_html_includes_flow_bottleneck_ranking():
    source_finding = {
        "severity": "HIGH",
        "title": "Flow downstream database bottleneck",
        "impact": "Database latency is high while Kafka appears healthy.",
        "recommendation": "Inspect the downstream database before scaling Kafka.",
        "file": "examples/supported/runtime/flow-runtime.yaml",
        "rule_id": "flow.runtime.downstream_db_bottleneck",
        "evidence": {"flow": "checkout", "db_latency_ms": 900},
    }
    source_anchor = finding_anchor_id(source_finding)
    diagnostic_summary = {
        "diagnostic_status": "ROOT_CAUSE_CANDIDATES_FOUND",
        "executive_summary": "Beacon found a flow bottleneck.",
        "primary_hypothesis": None,
        "first_actions": [],
        "diagnostic_playbooks": [],
        "operational_decisions": [
            {
                "rank": 1,
                "decision_label": "Downstream Database Bottleneck",
                "action": "Inspect database pool before scaling Kafka.",
                "target": "database",
                "disposition": "investigate_before_action",
                "safety": "SAFE",
                "confidence": "HIGH",
                "decision_type": "incident_action",
                "why": "Beacon ranked database as the likely bottleneck.",
                "evidence_required": ["database connection pool utilization"],
                "do_not_do": ["Do not scale Kafka first."],
                "source_rule_ids": ["flow.runtime.downstream_db_bottleneck"],
            }
        ],
        "consumer_group_diagnoses": [],
        "flow_bottleneck_rankings": [
            {
                "flow": "checkout",
                "owner": "team-checkout",
                "criticality": "critical",
                "business_impact": "Checkout payment completion can fail.",
                "affected_services": ["payments", "orders"],
                "incident_priority": "P1",
                "flow_path": [
                    {
                        "component": "api",
                        "component_type": "api",
                        "label": "api",
                        "status": "possible_bottleneck",
                        "confidence": "MEDIUM",
                        "is_bottleneck": False,
                        "evidence_used": ["HIGH: API timeout signal"],
                        "evidence_missing": [
                            "API latency and error trend before/after the incident window"
                        ],
                        "inspect_next": ["Inspect endpoint latency and retry dashboards first."],
                        "source_findings": [
                            {
                                "severity": "HIGH",
                                "rule_id": "api.runtime.timeout_rate.high",
                                "title": "API timeout signal",
                                "file": "examples/supported/runtime/flow-runtime.yaml",
                                "anchor": "finding-api-runtime-timeout-rate-high",
                            }
                        ],
                    },
                    {
                        "component": "database",
                        "component_type": "database",
                        "label": "database",
                        "status": "likely_bottleneck",
                        "confidence": "HIGH",
                        "is_bottleneck": True,
                        "evidence_used": ["HIGH: Flow downstream database bottleneck"],
                        "evidence_missing": ["database connection pool utilization"],
                        "inspect_next": ["Inspect connection pools and slow queries."],
                        "source_findings": [
                            {
                                "severity": "HIGH",
                                "rule_id": "flow.runtime.downstream_db_bottleneck",
                                "title": "Flow downstream database bottleneck",
                                "file": "examples/supported/runtime/flow-runtime.yaml",
                                "anchor": source_anchor,
                            }
                        ],
                    },
                ],
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
        [source_finding],
        score=0,
        open_report=False,
        diagnostic_summary=diagnostic_summary,
    )

    out_path = os.path.join("reports", "report.html")
    with open(out_path, "r") as f:
        html = f.read()

    assert "Flow Bottleneck Ranking" in html
    assert "Runtime Operational Decisions" in html
    assert "Downstream Database Bottleneck" in html
    assert "Inspect database pool before scaling Kafka" in html
    assert "Do not scale Kafka first" in html
    assert "database" in html
    assert "team-checkout" in html
    assert "Checkout payment completion can fail" in html
    assert "Flow path" in html
    assert "bottleneck" in html
    assert "Evidence Used" in html
    assert "Evidence Missing" in html
    assert "Inspect Next" in html
    assert "Source Findings" in html
    assert f'href="#{source_anchor}"' in html
    assert f'id="{source_anchor}"' in html
    assert "API timeout signal" in html
    assert "database connection pool utilization" in html


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
