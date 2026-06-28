# Community Discussion Prompts

Beacon is still evolving, and the most useful feedback is specific: which check
was useful, which check was noisy, and which operational scenario Beacon should
reason about next.

Use these discussion prompts when GitHub Discussions are enabled for the repo.
They also work as copy/paste prompts for issues, pull requests, or community
posts.

## 1. Readiness Scoring And Decision Synthesis

Question:

```text
How does the readiness scoring engine combine Kafka replication factors with
consumer lag and broker disk pressure into one decision?
```

Relevant code:

- `beacon/engine/rule_direction.py`
- `beacon/readiness/interpretation.py`

Discussion template:

- `.github/DISCUSSION_TEMPLATE/readiness-scoring.md`

## 2. IaC Coverage Readiness

Question:

```text
What does the IaC coverage pack do, and how does it compare cloud inventory to
Terraform state?
```

Relevant code:

- `beacon/iac_coverage.py`
- `packs/iac-coverage-readiness/`

Discussion template:

- `.github/DISCUSSION_TEMPLATE/iac-coverage-readiness.md`

## 3. Custom Policies And Rules

Question:

```text
Can I add custom rules or policies to Beacon, and how?
```

Relevant code:

- `beacon/policy.py`
- `examples/product-readiness/dev-exception/beacon-policy.yaml`

Current boundary:

```text
Policy injection supports overrides and waivers today. Readiness packs are
introspectable. New executable rules are currently defined internally by
Beacon's registered rule system.
```

Discussion template:

- `.github/DISCUSSION_TEMPLATE/custom-policies-and-rules.md`
