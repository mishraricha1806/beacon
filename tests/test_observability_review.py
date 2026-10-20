import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from beacon.cli import app
from beacon.evidence_quality import annotate_evidence_quality
from beacon.observability_review import (
    analyze_observability_review,
    analyze_observability_review_file,
)
from beacon.packs import get_pack, validate_pack

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def healthy_review():
    return {
        "schema_version": "1.0.0",
        "captured_at": "2026-09-06T08:00:00Z",
        "freshness_policy": {"max_age_hours": 24},
        "service": {"name": "checkout", "owner": "team-checkout", "tier": "tier-1"},
        "slos": [
            {
                "name": "availability",
                "target_percent": 99.9,
                "window_days": 28,
                "error_budget_remaining_percent": 70,
                "burn_rate_alerts": [
                    {"window": "5m", "threshold": 14.4},
                    {"window": "1h", "threshold": 6},
                ],
            }
        ],
        "alerts": [
            {
                "name": "fast-burn",
                "owner": "team-checkout",
                "route": "pagerduty-checkout",
                "severity": "critical",
                "runbook_url": "https://runbooks.example/checkout",
            }
        ],
        "dashboards": [
            {
                "name": "checkout",
                "owner": "team-checkout",
                "url": "https://grafana.example/checkout",
                "signals": ["availability", "latency", "traffic", "errors", "saturation"],
            }
        ],
        "telemetry": {
            "signals": {"metrics": True, "logs": True, "traces": True},
            "trace_sampling_ratio": 0.1,
            "trace_propagation_verified": True,
            "correlations": ["logs_to_traces", "metrics_to_traces"],
            "active_series": 100,
            "active_series_budget": 200,
            "monthly_cost": 1000,
            "monthly_cost_budget": 2000,
            "sensitive_fields_detected": [],
        },
        "synthetics": [{"name": "checkout", "enabled": True, "owner": "team-checkout"}],
        "incidents": [],
        "deployments": [],
        "history": {"minimum_snapshots": 3, "snapshots": [{}, {}, {}]},
    }


def test_healthy_review_verifies_controls_and_annotates_evidence_quality():
    findings = analyze_observability_review(healthy_review(), now=NOW)

    assert [item["rule_id"] for item in findings] == ["observability.review.controls_verified"]
    assessment = findings[0]["evidence"]["assessment"]
    assert assessment == {
        "confidence": "MEDIUM",
        "freshness": "CURRENT",
        "evidence_bound": True,
    }


def test_review_detects_governance_quality_cost_security_and_regression_risks():
    review = healthy_review()
    review["service"]["owner"] = None
    review["slos"][0]["error_budget_remaining_percent"] = 0
    review["slos"][0]["burn_rate_alerts"] = [{"window": "5m", "threshold": 14.4}]
    review["alerts"][0].pop("runbook_url")
    review["dashboards"][0]["signals"] = ["latency", "errors"]
    review["telemetry"].update(
        {
            "signals": {"metrics": True, "logs": False, "traces": True},
            "trace_propagation_verified": False,
            "correlations": [],
            "trace_sampling_ratio": 0,
            "active_series": 300,
            "active_series_budget": 200,
            "monthly_cost": 3000,
            "monthly_cost_budget": 2000,
            "sensitive_fields_detected": ["http.authorization", "customer.email"],
        }
    )
    review["synthetics"] = []
    review["incidents"] = [{"id": "INC-1", "started_at": "2026-09-05T10:00:00Z"}]
    review["history"]["snapshots"] = [{}]
    review["deployments"] = [
        {
            "id": "deploy-1",
            "before": {"error_rate_percent": 1},
            "after": {"error_rate_percent": 4},
        }
    ]

    findings = analyze_observability_review(review, now=NOW)
    ids = {item["rule_id"] for item in findings}

    assert {
        "observability.service.owner_missing",
        "observability.error_budget.exhausted",
        "observability.slo.burn_rate_multi_window_missing",
        "observability.alert.governance_incomplete",
        "observability.dashboard.critical_signals_missing",
        "observability.telemetry.signals_missing",
        "observability.trace.propagation_unverified",
        "observability.telemetry.correlation_incomplete",
        "observability.telemetry.sampling_invalid",
        "observability.metrics.cardinality_budget_exceeded",
        "observability.telemetry.cost_budget_exceeded",
        "observability.telemetry.sensitive_data_detected",
        "observability.synthetic.coverage_missing",
        "observability.incident.timeline_incomplete",
        "observability.history.insufficient",
        "observability.deployment.regression_detected",
    }.issubset(ids)
    assert all(item["evidence"]["assessment"]["evidence_bound"] for item in findings)


def test_stale_evidence_blocks_analysis():
    review = healthy_review()
    review["captured_at"] = "2026-09-01T08:00:00Z"

    findings = analyze_observability_review(review, now=NOW)
    stale = next(item for item in findings if item["rule_id"] == "observability.evidence.stale")

    assert stale["severity"] == "ERROR"
    assert stale["evidence"]["assessment"]["freshness"] == "STALE"


def test_stale_signal_and_degrading_history_are_reported():
    review = healthy_review()
    review["telemetry"]["max_signal_age_minutes"] = 15
    review["telemetry"]["last_seen_at"] = {
        "metrics": "2026-09-06T11:00:00Z",
        "logs": "not-a-timestamp",
        "traces": "2026-09-06T11:59:00Z",
    }
    review["history"]["snapshots"] = [
        {"metrics": {"latency_p95_ms": 100}},
        {"metrics": {"latency_p95_ms": 120}},
        {"metrics": {"latency_p95_ms": 160}},
    ]

    findings = analyze_observability_review(review, now=NOW)
    ids = {item["rule_id"] for item in findings}

    assert "observability.telemetry.data_stale" in ids
    assert "observability.history.degrading_trend" in ids
    stale = next(
        item for item in findings if item["rule_id"] == "observability.telemetry.data_stale"
    )
    assert stale["evidence"]["stale_signal_age_minutes"] == {
        "metrics": 60.0,
        "logs": None,
    }


def test_invalid_contract_and_invalid_file_are_analysis_errors(tmp_path):
    invalid_contract = analyze_observability_review({"schema_version": "2.0.0"}, now=NOW)
    assert invalid_contract[0]["rule_id"] == "observability.review.input_invalid"
    assert invalid_contract[0]["severity"] == "ERROR"

    path = tmp_path / "broken.yaml"
    path.write_text("observability_review: [", encoding="utf-8")
    invalid_file = analyze_observability_review_file(path, now=NOW)
    assert invalid_file[0]["rule_id"] == "observability.review.input_invalid"

    invalid_shape = analyze_observability_review(
        {"schema_version": "1.0.0", "telemetry": []}, now=NOW
    )
    assert invalid_shape[0]["evidence"]["error"] == "telemetry must be an object."


def test_observability_schema_pack_fixture_and_cli_contract():
    schema = json.loads(
        (ROOT / "beacon/schemas/observability-review-v1.schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["observability_review"]["properties"]["schema_version"] == {
        "const": "1.0.0"
    }

    pack = get_pack("observability-production-readiness")
    validation = validate_pack(pack)
    assert validation["valid"] is True
    assert validation["missing_metadata"] == []

    result = CliRunner().invoke(
        app,
        [
            "readiness",
            "observability",
            str(ROOT / "examples/supported/observability/checkout-observability.yaml"),
            "--no-html",
            "--no-open-report",
            "--output",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0.0"
    assert payload["findings"][0]["rule_id"] == "observability.review.controls_verified"


def test_generic_findings_receive_explicit_evidence_quality_without_overwriting_domain_data():
    findings = [
        {"evidence": {"resource": "api"}},
        {
            "evidence": {
                "assessment": {
                    "confidence": "HIGH",
                    "freshness": "CURRENT",
                    "evidence_bound": True,
                }
            }
        },
    ]

    annotate_evidence_quality(findings, now=NOW)

    assert findings[0]["evidence"]["assessment"]["freshness"] == "UNKNOWN"
    assert findings[0]["evidence"]["assessment"]["evidence_bound"] is True
    assert findings[1]["evidence"]["assessment"]["confidence"] == "HIGH"
