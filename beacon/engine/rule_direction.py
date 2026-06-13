"""Rule evaluation direction and flow.

This module documents the clear, deterministic flow of rule evaluation:

  1. DATA INPUT (infrastructure configs, runtime metrics, snapshots)
         ↓
  2. RULE EVALUATION (independent rules execute against data)
         ↓
  3. FINDING GENERATION (rules produce findings with evidence)
         ↓
  4. FINDING CLASSIFICATION (categorize by severity and risk area)
         ↓
  5. DECISION LOGIC (determine READY/NOT READY)
         ↓
  6. OUTPUT FORMATTING (standardized PRODUCTION DECISION output)

This direction ensures:
- Deterministic results (same input → same output)
- Explainable decisions (all findings visible)
- Trustworthy intelligence (no AI hallucinations)
- Operational clarity (clear next steps)
"""

from enum import Enum
from typing import List, Dict


class EvaluationPhase(Enum):
    """Phases of rule evaluation."""

    DATA_INPUT = "data_input"
    RULE_EVALUATION = "rule_evaluation"
    FINDING_GENERATION = "finding_generation"
    FINDING_CLASSIFICATION = "finding_classification"
    DECISION_LOGIC = "decision_logic"
    OUTPUT_FORMATTING = "output_formatting"


class RuleFlowManager:
    """Manages the rule evaluation flow from input to output."""

    def __init__(self):
        """Initialize flow manager."""
        self.current_phase = EvaluationPhase.DATA_INPUT
        self.flow_log: List[Dict] = []

    def log_phase_entry(self, phase: EvaluationPhase, context: Dict = None) -> None:
        """Log entry into a phase.

        Args:
            phase: Current phase
            context: Phase-specific context data
        """
        self.current_phase = phase
        self.flow_log.append(
            {
                "phase": phase.value,
                "event": "entry",
                "context": context or {},
            }
        )

    def log_phase_exit(self, phase: EvaluationPhase, context: Dict = None) -> None:
        """Log exit from a phase.

        Args:
            phase: Current phase
            context: Phase-specific context data
        """
        self.flow_log.append(
            {
                "phase": phase.value,
                "event": "exit",
                "context": context or {},
            }
        )

    def get_flow_log(self) -> List[Dict]:
        """Get complete flow log.

        Returns:
            List of flow events
        """
        return self.flow_log

    @staticmethod
    def validate_finding(finding: Dict) -> bool:
        """Validate a finding has required fields.

        Args:
            finding: Finding dict

        Returns:
            True if valid, raises ValueError otherwise
        """
        required_fields = ["severity", "title", "impact", "recommendation", "file"]
        missing = [f for f in required_fields if f not in finding]

        if missing:
            raise ValueError(f"Finding missing required fields: {missing}")

        return True

    @staticmethod
    def validate_severity(severity: str) -> bool:
        """Validate finding severity.

        Args:
            severity: Severity string

        Returns:
            True if valid

        Raises:
            ValueError if invalid
        """
        valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "ERROR"]
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity: {severity}. Must be one of {valid_severities}")
        return True
