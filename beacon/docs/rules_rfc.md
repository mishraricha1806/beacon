# Beacon Rule Registry RFC

Status: Implemented for Module 1 static readiness


Date: 2026-05-23

## Goal

Define a minimal, production-ready Rule Registry and metadata format for Beacon's deterministic rule engine. The registry enables provenance, governance, UI integration, and easier rule lifecycle management while keeping rule evaluation deterministic and testable.

This RFC describes:
- rule metadata schema
- on-disk format and loading
- runtime representation
- rule provenance in findings
- migration and backward-compatibility considerations
- recommended developer workflow

## Motivation

Module 1 (Production Readiness Intelligence) must produce deterministic findings with clear evidence and a stable identifier for each rule. Enterprises require auditability, explainability, and the ability to manage rules (enable/disable, change severity, track authorship).

Current state: static readiness rules are registered resource-driven checks. Raw Terraform, Kafka YAML, and Kubernetes YAML are normalized before evaluation, then executed through the shared registry/evaluator path.

## Requirements

- Every finding must include `rule_id` and `evidence` describing source/path/value that triggered it.
- Rules must expose metadata: title, description, default severity, category, author, version, recommendation, and optional remediation links.
- Support both programmatic rules (Python functions) and declarative rules (simple checks expressed in YAML) in the future.
- Backward compatibility: existing findings must still include old keys (severity, title, impact, recommendation, file).
- Rule metadata should be editable independently of code (e.g., YAML files) for non-engineer review.

## Rule metadata schema

Each rule will have a stable `rule_id` of the form `<domain>.<entity>.<short-name>` (e.g., `kafka.topic.replication_factor.low`).

Minimal metadata fields:

- rule_id (string) - stable identifier
- title (string) - short human-friendly title
- description (string) - rationale and why it matters
- severity_default (enum) - CRITICAL/HIGH/MEDIUM/LOW/ERROR
- category (string) - mapping to readiness categories (resiliency, scalability, storage_sustainability, operational_safety, recovery_readiness)
- author (string) - rule owner
- recommendation (string) - short remediation guidance
- version (string) - rule metadata version
- tags (list[string]) - optional tags

Example (YAML):

```yaml
rule_id: kafka.topic.replication_factor.low
title: Kafka topic replication factor below recommended minimum
description: |-
  Production Kafka topics should use replication_factor >= 3 for high availability.
severity_default: CRITICAL
category: resiliency
author: beacon.rules
recommendation: Set replication_factor=3 for production topics.
version: "1.0"
```

## On-disk layout & loading

Start with a simple `beacon/rules_metadata.py` (Python dict) for now (fast). Later we will move to `rules/metadata/*.yaml` with a loader.

Loading rules:
- At module import or startup, load `beacon.rules_metadata.RULES` dict into an in-memory registry.
- Provide a small API:
  - `rules_registry.get(rule_id)` → metadata
  - `rules_registry.list()`
  - `rules_registry.override(rule_id, **overrides)` (for runtime policy)

## Runtime representation & findings

Findings will include new keys:
- `rule_id` (optional if produced by non-rule logic)
- `evidence` (dict) with keys: `source`, `path`, `value`, and domain-specific extras (e.g., offending_keys).

Findings retain existing keys for backward compatibility.

Example finding:

```json
{
  "rule_id": "kafka.topic.replication_factor.low",
  "severity": "CRITICAL",
  "title": "Kafka topic 'payments' has replication factor 1",
  "impact": "A broker failure can make this topic unavailable...",
  "recommendation": "Use replication_factor=3 for production topics.",
  "file": "examples/bad-infra/kafka-topics.yaml",
  "evidence": {
    "source": "file",
    "path": "topics[0].replication_factor",
    "value": 1
  }
}
```

## Rule evaluation model

Two approaches supported:

1. Registered Python rules (current): small functions that evaluate normalized resources and return structured findings with `rule_id` and `evidence`.
2. Declarative rules (future): small YAML-based checks (e.g., threshold, presence) that run via a generic evaluator.

Module 1 rollout: route static analysis through normalized resources, the rule registry, and the shared evaluator. Legacy `evaluate_*` imports are compatibility shims only.

## Governance & lifecycle

- Rule authors update metadata in `rules/metadata/*.yaml` and create PRs for changes.
- Version policy: bump `version` in metadata when changing semantics.
- Runtime policy overrides: platform operators can provide a `policy.yaml` to adjust severity or disable rules per environment.

## Backward compatibility

- Findings without `rule_id` remain valid; new code should prefer `rule_id` when present.
- The `print_report` and HTML rendering will display `rule_id` and `evidence` when present, but still show existing fields.

## Developer workflow

- Add or modify a rule: implement a registered rule in `beacon/rules/*_registered_rules.py`, ensure the normalizer emits the required resource attributes, and add metadata in `beacon/rules/metadata/*.yaml`.
- Add unit tests: provide positive and negative example inputs and assert that `evaluate_*` returns findings with expected `rule_id` and `evidence`.
- For declarative rules: add YAML in `beacon/rules/metadata/` and update loader.

## Next steps / roadmap

Completed for Module 1:
- Static scanner uses normalized resources before rule evaluation.
- Kafka, Terraform object storage/IAM, and Kubernetes readiness rules run through the shared registry/evaluator.
- Findings include `rule_id`, `domain`, `category`, `evidence`, and remediation fields.
- Metadata is loaded from YAML under `beacon/rules/metadata/`.
- Runtime policy overrides apply before readiness scoring.

Next:
- Add a declarative rule DSL for low-complexity presence/threshold checks.
- Add UI wireframes to display rule provenance, evidence, and remediation links.

Long-term:
- Add a declarative rule DSL for basic checks.
- Add rule audit trails (who changed a rule and when) and automatic change impact analysis.

## Open questions

- Do we want rule IDs to follow a stricter naming convention (e.g., semantic segments)? Proposal: `<domain>.<resource>.<check>`, optional subtypes e.g., `kafka.topic.replication_factor.low`.
- Where should runtime policy overrides live? Candidate: `~/.beacon/policy.yaml` or CI-driven config per environment.

