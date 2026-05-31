from pathlib import Path

from beacon.opentelemetry_connector import analyze_opentelemetry_file
from beacon.prometheus_connector import analyze_prometheus_config
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.runtime_snapshot import analyze_runtime_snapshot_file
from beacon.scanner import scan_path


ROOT = Path("examples/supported")


SUMMARY_KEYS = {
    "score",
    "score_status",
    "production_decision",
    "survivability",
    "categories",
    "primary_risk_area",
    "top_reasons",
    "next_best_actions",
    "root_cause_hypotheses",
}

FINDING_KEYS = {
    "rule_id",
    "severity",
    "title",
    "impact",
    "recommendation",
    "file",
    "evidence",
}

HYPOTHESIS_KEYS = {
    "correlation_id",
    "title",
    "confidence",
    "score",
    "evidence",
    "matched_rule_ids",
    "recommendation",
}


def rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def assert_release_summary(summary):
    assert SUMMARY_KEYS <= set(summary)
    assert isinstance(summary["score"], int)
    assert summary["score_status"] in {
        "CALCULATED",
        "BLOCKED_BY_ANALYSIS_ERROR",
    }
    assert summary["production_decision"] in {
        "READY",
        "READY WITH RISKS",
        "NOT READY",
    }
    assert isinstance(summary["categories"], dict)
    assert isinstance(summary["root_cause_hypotheses"], list)


def assert_release_findings(findings):
    assert findings
    for finding in findings:
        assert FINDING_KEYS <= set(finding)
        assert finding["severity"] in {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
            "INFO",
            "ERROR",
        }


def assert_release_hypotheses(summary):
    hypotheses = summary["root_cause_hypotheses"]
    assert hypotheses

    top_hypothesis = hypotheses[0]
    assert HYPOTHESIS_KEYS <= set(top_hypothesis)
    assert top_hypothesis["confidence"] in {"LOW", "MEDIUM", "HIGH"}
    assert top_hypothesis["evidence"]
    assert top_hypothesis["matched_rule_ids"]


def test_module1_static_supported_examples_contract():
    findings = scan_path(str(ROOT))
    summary = calculate_readiness(findings)

    assert_release_findings(findings)
    assert_release_summary(summary)

    ids = rule_ids(findings)
    assert "object_storage.public_access.enabled" in ids
    assert "kafka.topic.replication_factor.low" in ids
    assert "k8s.container.privileged" in ids
    assert "cicd.github.permissions.write_all" in ids
    assert "topology.service.blast_radius.high" in ids


def test_module1_runtime_snapshot_contract():
    findings = analyze_runtime_snapshot_file(str(ROOT / "runtime" / "all-runtime.yaml"))
    summary = calculate_readiness(findings)

    assert_release_findings(findings)
    assert_release_summary(summary)
    assert_release_hypotheses(summary)

    ids = rule_ids(findings)
    assert "flow.runtime.cascading_latency" in ids
    assert "api.runtime.retry_amplification" in ids
    assert "database.runtime.connection_pool.exhaustion" in ids
    assert "storage.runtime.backup_stale" in ids


def test_module1_opentelemetry_contract():
    findings = analyze_opentelemetry_file(
        str(ROOT / "opentelemetry" / "checkout-otel.yaml")
    )
    summary = calculate_readiness(findings)

    assert_release_findings(findings)
    assert_release_summary(summary)
    assert_release_hypotheses(summary)

    ids = rule_ids(findings)
    assert "opentelemetry.runtime.read_only_mode" in ids
    assert "flow.runtime.cascading_latency" in ids
    assert "database.runtime.connection_pool.exhaustion" in ids


def test_module1_prometheus_failure_blocks_readiness(monkeypatch):
    import beacon.prometheus_connector as prometheus_connector

    def fail_query(*args, **kwargs):
        raise RuntimeError("prometheus unavailable")

    monkeypatch.setattr(prometheus_connector, "query_prometheus", fail_query)

    findings = analyze_prometheus_config(
        str(ROOT / "prometheus" / "platform-prometheus.yaml"),
        timeout=1,
    )
    summary = calculate_readiness(findings)

    assert_release_findings(findings)
    assert_release_summary(summary)
    assert "prometheus.query.failed" in rule_ids(findings)
    assert summary["error"] > 0
    assert summary["score_status"] == "BLOCKED_BY_ANALYSIS_ERROR"
    assert summary["survivability"] == "ANALYSIS BLOCKED"
    assert summary["production_decision"] == "NOT READY"


def test_module1_json_payload_contract_shape():
    findings = analyze_runtime_snapshot_file(str(ROOT / "runtime" / "all-runtime.yaml"))
    summary = calculate_readiness(findings)

    payload = {
        "score": summary["score"],
        "score_status": summary["score_status"],
        "readiness_summary": summary,
        "findings": findings,
    }

    assert set(payload) == {
        "score",
        "score_status",
        "readiness_summary",
        "findings",
    }
    assert_release_summary(payload["readiness_summary"])
    assert_release_findings(payload["findings"])
