"""Standardized output formatting for production decisions.

This module ensures all Beacon outputs conform to the standard format:
  PRODUCTION DECISION: READY | NOT READY
  Primary Risk Area: ...
  Next Best Actions: ...
"""

from typing import Dict, List, Optional
from beacon.decisions.decision_engine import DecisionEngine, ProductionDecision


class DecisionFormatter:
    """Formats production decisions for clear human-readable output."""

    @staticmethod
    def format_production_decision(
        decision: ProductionDecision,
        findings: List[Dict],
        score: int,
        reasoning: str,
        analysis_type: str = "General",
    ) -> str:
        """Format production decision for terminal output.

        Args:
            decision: ProductionDecision enum value
            findings: List of findings
            score: Readiness score (0-100)
            reasoning: Decision reasoning text
            analysis_type: Type of analysis (Static, Runtime, Snapshot)

        Returns:
            Formatted string for terminal output
        """
        lines = [
            "\n" + "=" * 70,
            "BEACON PRODUCTION DECISION",
            "=" * 70,
            "",
            f"DECISION: {decision.value}",
            "",
            f"Production Readiness Score: {score}/100",
            f"Analysis Type: {analysis_type}",
            f"Reasoning: {reasoning}",
            "",
        ]

        # Risk categories
        categorized = DecisionEngine.categorize_findings(findings)
        if any(categorized[k] for k in ["CRITICAL", "HIGH"]):
            lines.append("=" * 70)
            lines.append("PRIMARY RISK AREAS")
            lines.append("=" * 70)
            lines.append("")

            risk_areas = DecisionEngine.identify_primary_risk_areas(findings)
            for idx, area in enumerate(risk_areas[:3], 1):
                lines.append(f"[{area['max_severity']}] {area['area']}: {area['count']} finding(s)")
                # Show first finding for context
                if area["findings"]:
                    first = area["findings"][0]
                    lines.append(f"       {first['title'][:60]}...")
                lines.append("")

        # Remediation actions
        lines.append("=" * 70)
        lines.append("NEXT BEST ACTIONS (Prioritized)")
        lines.append("=" * 70)
        lines.append("")

        actions = DecisionEngine.prioritize_remediation_actions(findings, max_actions=5)
        if actions:
            for idx, action in enumerate(actions, 1):
                lines.append(f"{idx}. [{action['severity']}] {action['title']}")
                lines.append(f"   Action: {action['recommendation']}")
                lines.append(f"   Impact: {action['impact']}")
                lines.append("")
        else:
            lines.append("No critical actions required.")
            lines.append("")

        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def format_json_decision(
        decision: ProductionDecision,
        findings: List[Dict],
        score: int,
        reasoning: str,
        analysis_type: str = "General",
        readiness_summary: Optional[Dict] = None,
    ) -> Dict:
        """Format production decision as JSON.

        Returns:
            JSON-serializable dict
        """
        categorized = DecisionEngine.categorize_findings(findings)
        risk_areas = DecisionEngine.identify_primary_risk_areas(findings)
        actions = DecisionEngine.prioritize_remediation_actions(findings, max_actions=5)

        return {
            "production_decision": decision.value,
            "score": score,
            "analysis_type": analysis_type,
            "reasoning": reasoning,
            "findings_summary": {
                "total": len(findings),
                "critical": len(categorized["CRITICAL"]),
                "high": len(categorized["HIGH"]),
                "medium": len(categorized["MEDIUM"]),
                "low": len(categorized["LOW"]),
            },
            "primary_risk_areas": [
                {
                    "area": area["area"],
                    "severity": area["max_severity"],
                    "finding_count": area["count"],
                }
                for area in risk_areas[:5]
            ],
            "next_best_actions": [
                {
                    "priority": idx + 1,
                    "severity": action["severity"],
                    "title": action["title"],
                    "recommendation": action["recommendation"],
                    "impact": action["impact"],
                }
                for idx, action in enumerate(actions)
            ],
            "findings": findings,
            "readiness_summary": readiness_summary,
        }
