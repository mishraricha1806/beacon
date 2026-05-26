"""Core rule evaluation engine.

This module implements the stable rule engine direction:
  Rules → Findings → Classification → Decision

This is the central nervous system of Beacon's deterministic intelligence.
"""

from typing import List, Dict, Callable, Any
from dataclasses import dataclass


@dataclass
class Rule:
    """Represents a single evaluation rule."""
    rule_id: str
    title: str
    category: str
    severity_default: str
    description: str
    evaluator: Callable[[Dict], List[Dict]]


class RulesEngine:
    """Core rule evaluation engine."""

    def __init__(self):
        """Initialize the rules engine."""
        self.rules: Dict[str, Rule] = {}
        self.execution_log: List[Dict] = []

    def register_rule(self, rule: Rule) -> None:
        """Register a rule for evaluation.

        Args:
            rule: Rule instance
        """
        if rule.rule_id in self.rules:
            raise ValueError(f"Rule {rule.rule_id} already registered")
        self.rules[rule.rule_id] = rule

    def evaluate(
        self,
        data: Dict[str, Any],
        rule_ids: List[str] = None
    ) -> List[Dict]:
        """Evaluate rules against data.

        Args:
            data: Data to evaluate
            rule_ids: Specific rules to evaluate (None = all)

        Returns:
            List of findings
        """
        findings = []
        rules_to_evaluate = rule_ids or list(self.rules.keys())

        for rule_id in rules_to_evaluate:
            if rule_id not in self.rules:
                raise ValueError(f"Rule {rule_id} not found")

            rule = self.rules[rule_id]

            try:
                # Execute the rule evaluator
                rule_findings = rule.evaluator(data)

                # Tag findings with rule metadata
                for finding in rule_findings:
                    if "rule_id" not in finding:
                        finding["rule_id"] = rule_id
                    if "category" not in finding:
                        finding["category"] = rule.category

                findings.extend(rule_findings)

                # Log execution
                self.execution_log.append({
                    "rule_id": rule_id,
                    "status": "success",
                    "findings_count": len(rule_findings),
                })

            except Exception as e:
                # Log execution error
                self.execution_log.append({
                    "rule_id": rule_id,
                    "status": "error",
                    "error": str(e),
                })

        return findings

    def list_rules(self) -> Dict[str, Dict]:
        """List all registered rules with metadata.

        Returns:
            Dict of rule metadata
        """
        return {
            rule_id: {
                "rule_id": rule.rule_id,
                "title": rule.title,
                "category": rule.category,
                "severity_default": rule.severity_default,
                "description": rule.description,
            }
            for rule_id, rule in self.rules.items()
        }

    def get_execution_log(self) -> List[Dict]:
        """Get rule execution log.

        Returns:
            List of execution events
        """
        return self.execution_log

    def clear_execution_log(self) -> None:
        """Clear execution log."""
        self.execution_log = []
