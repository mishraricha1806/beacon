from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class Rule:
    rule_id: str
    domain: str
    category: str
    severity: str
    title: str
    evaluator: Callable
    supported_types: List[str]
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
