from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class Resource:
    type: str
    name: str
    domain: str
    source: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    domain: str
    category: str
    severity: str
    title: str
    description: str
    supported_resource_types: List[str]
    evaluator: Callable
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(frozen=True)
class Finding:
    rule_id: str
    domain: str
    category: str
    severity: str
    title: str
    impact: str
    recommendation: str
    file: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "domain": self.domain,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "file": self.file,
            "evidence": self.evidence,
            "tags": self.tags,
        }
