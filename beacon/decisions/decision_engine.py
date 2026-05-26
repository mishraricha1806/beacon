"""Core decision engine for production readiness determination.

This module implements the deterministic production decision logic.
It converts findings into actionable READY/NOT READY decisions.
"""

from typing import Dict, List, Tuple
from enum import Enum


class ProductionDecision(Enum):
    """Production readiness decision."""
    READY = "READY"
    NOT_READY = "NOT READY"


class RiskLevel(Enum):
    """Risk severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionEngine:
    """Engine for determining production readiness based on findings."""

    # Decision thresholds
    CRITICAL_THRESHOLD = 0  # Any critical finding = NOT READY
    HIGH_THRESHOLD = 2  # More than 2 high = consider NOT READY
    SCORE_THRESHOLD = 50  # Score below 50 = NOT READY

    @staticmethod
    def determine_production_decision(
        findings: List[Dict],
        score: int
    ) -> Tuple[ProductionDecision, str]:
        """Determine if system is production ready.

        Args:
            findings: List of finding dicts with 'severity' field
            score: Production readiness score (0-100)

        Returns:
            Tuple of (ProductionDecision, reasoning)
        """
        # Count findings by severity
        critical_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in findings if f.get("severity") == "HIGH")

        reasoning_parts = []

        # Rule 1: Any critical finding = NOT READY
        if critical_count > 0:
            reasoning_parts.append(
                f"System has {critical_count} critical finding(s) that must be resolved before production."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # Rule 2: Too many high-severity findings = NOT READY
        if high_count > DecisionEngine.HIGH_THRESHOLD:
            reasoning_parts.append(
                f"System has {high_count} high-severity findings. "
                f"More than {DecisionEngine.HIGH_THRESHOLD} high findings indicates operational risk."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # Rule 3: Low score = NOT READY
        if score < DecisionEngine.SCORE_THRESHOLD:
            reasoning_parts.append(
                f"Production readiness score ({score}/100) is below minimum threshold ({DecisionEngine.SCORE_THRESHOLD})."
            )
            return ProductionDecision.NOT_READY, " ".join(reasoning_parts)

        # All checks passed
        reasoning_parts.append(
            f"System meets production readiness criteria. "
            f"Score: {score}/100, Critical: {critical_count}, High: {high_count}."
        )
        return ProductionDecision.READY, " ".join(reasoning_parts)

    @staticmethod
    def categorize_findings(
        findings: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Categorize findings by severity and risk area.

        Returns:
            Dict mapping severity level to list of findings
        """
        categorized = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": [],
            "ERROR": [],
        }

        for finding in findings:
            severity = finding.get("severity", "MEDIUM")
            if severity in categorized:
                categorized[severity].append(finding)

        return categorized

    @staticmethod
    def identify_primary_risk_areas(
        findings: List[Dict]
    ) -> List[Dict]:
        """Identify primary risk areas from findings.

        Returns:
            List of risk area summaries, ordered by criticality
        """
        risk_areas = {}

        for finding in findings:
            # Extract risk category from title or rule_id
            rule_id = finding.get("rule_id", "")
            title = finding.get("title", "")
            severity = finding.get("severity", "MEDIUM")

            # Infer risk area from rule_id (e.g., "kafka.topic.replication_factor.min" -> "Kafka Topic Configuration")
            if rule_id.startswith("kafka"):
                risk_area = "Kafka Configuration"
            elif rule_id.startswith("aws.s3"):
                risk_area = "Object Storage Access Control"
            elif rule_id.startswith("iam"):
                risk_area = "IAM Permissions"
            else:
                risk_area = title.split(":")[0] if ":" in title else "General Risk"

            if risk_area not in risk_areas:
                risk_areas[risk_area] = {
                    "area": risk_area,
                    "count": 0,
                    "max_severity": severity,
                    "findings": [],
                }

            risk_areas[risk_area]["count"] += 1
            risk_areas[risk_area]["findings"].append(finding)

            # Update max severity
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            if severity_order.get(severity, 99) < severity_order.get(risk_areas[risk_area]["max_severity"], 99):
                risk_areas[risk_area]["max_severity"] = severity

        # Sort by severity and count
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_areas = sorted(
            risk_areas.values(),
            key=lambda x: (severity_order.get(x["max_severity"], 99), -x["count"])
        )

        return sorted_areas

    @staticmethod
    def prioritize_remediation_actions(
        findings: List[Dict],
        max_actions: int = 5
    ) -> List[Dict]:
        """Prioritize remediation actions based on impact and severity.

        Returns:
            List of prioritized action recommendations
        """
        actions = []

        # Score each finding
        severity_scores = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}

        for finding in findings:
            severity = finding.get("severity", "MEDIUM")
            score = severity_scores.get(severity, 50)

            action = {
                "priority_score": score,
                "severity": severity,
                "title": finding.get("title", "Unknown issue"),
                "recommendation": finding.get("recommendation", "Review and remediate"),
                "impact": finding.get("impact", "Operational risk"),
                "evidence": finding.get("evidence"),
            }
            actions.append(action)

        # Sort by priority score (highest first)
        actions.sort(key=lambda x: x["priority_score"], reverse=True)

        # Return top N actions
        return actions[:max_actions]
