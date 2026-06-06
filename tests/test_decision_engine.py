"""Tests for decision engine and standardized output."""

import pytest
from beacon.decisions.decision_engine import (
    DecisionEngine,
    ProductionDecision,
)
from beacon.decisions.decision_formatter import DecisionFormatter
from beacon.rules import finding


class TestDecisionEngine:
    """Test production decision logic."""

    def test_ready_decision_no_findings(self):
        """Test READY decision with no findings."""
        decision, reason = DecisionEngine.determine_production_decision(findings=[], score=100)
        assert decision == ProductionDecision.READY
        assert "ready" in reason.lower()

    def test_not_ready_critical_finding(self):
        """Test NOT READY decision with critical finding."""
        findings = [
            finding(
                "CRITICAL",
                "Replication factor 1",
                "Data loss risk",
                "Increase RF",
                "test.yaml",
            )
        ]
        decision, reason = DecisionEngine.determine_production_decision(findings=findings, score=80)
        assert decision == ProductionDecision.NOT_READY
        assert "critical" in reason.lower()

    def test_not_ready_low_score(self):
        """Test NOT READY decision with low score."""
        findings = [
            finding("HIGH", "Issue 1", "Impact", "Fix", "test.yaml"),
            finding("HIGH", "Issue 2", "Impact", "Fix", "test.yaml"),
            finding("MEDIUM", "Issue 3", "Impact", "Fix", "test.yaml"),
        ]
        decision, reason = DecisionEngine.determine_production_decision(findings=findings, score=45)
        assert decision == ProductionDecision.NOT_READY
        assert "below" in reason.lower() or "threshold" in reason.lower()

    def test_ready_decision_acceptable_findings(self):
        """Test READY decision with acceptable findings."""
        findings = [
            finding("MEDIUM", "Minor issue", "Low impact", "Consider", "test.yaml"),
            finding("LOW", "Suggestion", "Very low impact", "Optional", "test.yaml"),
        ]
        decision, reason = DecisionEngine.determine_production_decision(findings=findings, score=85)
        assert decision == ProductionDecision.READY

    def test_categorize_findings(self):
        """Test finding categorization."""
        findings = [
            finding("CRITICAL", "C1", "Impact", "Fix", "test.yaml"),
            finding("CRITICAL", "C2", "Impact", "Fix", "test.yaml"),
            finding("HIGH", "H1", "Impact", "Fix", "test.yaml"),
            finding("MEDIUM", "M1", "Impact", "Fix", "test.yaml"),
        ]
        categorized = DecisionEngine.categorize_findings(findings)
        assert len(categorized["CRITICAL"]) == 2
        assert len(categorized["HIGH"]) == 1
        assert len(categorized["MEDIUM"]) == 1
        assert len(categorized["LOW"]) == 0

    def test_identify_primary_risk_areas(self):
        """Test identification of primary risk areas."""
        findings = [
            finding(
                "CRITICAL",
                "Kafka replication factor 1",
                "Data loss risk",
                "Increase RF",
                "kafka.yaml",
                rule_id="kafka.topic.replication_factor.low",
            ),
            finding(
                "HIGH",
                "Object storage public access",
                "Data exposure",
                "Block access",
                "storage.tf",
                rule_id="object_storage.public_access.enabled",
            ),
        ]
        risk_areas = DecisionEngine.identify_primary_risk_areas(findings)
        assert len(risk_areas) > 0
        # First should be Kafka (more critical)
        assert "Kafka" in risk_areas[0]["area"]

    def test_prioritize_remediation_actions(self):
        """Test prioritization of remediation actions."""
        findings = [
            finding("CRITICAL", "Critical issue", "Impact", "Action 1", "test.yaml"),
            finding("MEDIUM", "Medium issue", "Impact", "Action 2", "test.yaml"),
            finding("HIGH", "High issue", "Impact", "Action 3", "test.yaml"),
        ]
        actions = DecisionEngine.prioritize_remediation_actions(findings, max_actions=5)
        # Should be sorted: CRITICAL, HIGH, MEDIUM
        assert actions[0]["severity"] == "CRITICAL"
        assert actions[1]["severity"] == "HIGH"
        assert actions[2]["severity"] == "MEDIUM"

    def test_prioritize_actions_limited_count(self):
        """Test that action count is limited."""
        findings = [
            finding(
                f"{'CRITICAL' if i == 0 else 'HIGH'}",
                f"Issue {i}",
                "Impact",
                "Action",
                "test.yaml",
            )
            for i in range(10)
        ]
        actions = DecisionEngine.prioritize_remediation_actions(findings, max_actions=3)
        assert len(actions) == 3


class TestDecisionFormatter:
    """Test decision output formatting."""

    def test_format_production_decision_terminal(self):
        """Test terminal format output."""
        findings = [finding("CRITICAL", "Replication issue", "Data loss", "Fix now", "test.yaml")]
        output = DecisionFormatter.format_production_decision(
            decision=ProductionDecision.NOT_READY,
            findings=findings,
            score=70,
            reasoning="System has critical findings",
            analysis_type="Static",
        )
        assert "NOT READY" in output
        assert "70/100" in output
        assert "NEXT BEST ACTIONS" in output
        assert "PRIMARY RISK AREAS" in output

    def test_format_production_decision_json(self):
        """Test JSON format output."""
        findings = [
            finding(
                "HIGH",
                "Storage issue",
                "Disk pressure",
                "Review retention",
                "test.yaml",
            )
        ]
        output = DecisionFormatter.format_json_decision(
            decision=ProductionDecision.READY,
            findings=findings,
            score=75,
            reasoning="Acceptable operational state",
            analysis_type="Runtime",
        )
        assert output["production_decision"] == "READY"
        assert output["score"] == 75
        assert output["analysis_type"] == "Runtime"
        assert "findings_summary" in output
        assert "primary_risk_areas" in output
        assert "next_best_actions" in output

    def test_json_output_has_all_fields(self):
        """Test that JSON output includes all required fields."""
        findings = []
        output = DecisionFormatter.format_json_decision(
            decision=ProductionDecision.READY,
            findings=findings,
            score=100,
            reasoning="All clear",
            analysis_type="Static",
        )
        required_fields = [
            "production_decision",
            "score",
            "analysis_type",
            "findings_summary",
            "primary_risk_areas",
            "next_best_actions",
            "findings",
        ]
        for field in required_fields:
            assert field in output
