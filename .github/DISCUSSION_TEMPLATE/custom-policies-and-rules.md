---
name: Custom policies and rules
about: Discuss policy overrides, waivers, readiness packs, and future custom rule authoring
title: "Can I add custom rules or policies to Beacon?"
labels: policy, readiness-packs, product-feedback
---

## Question

Can users add custom rules or policies to Beacon, and what should that workflow
look like?

## Current implementation areas

- `beacon/policy.py`
- `examples/product-readiness/dev-exception/beacon-policy.yaml`
- `packs/`

Policy injection exists today for overrides and waivers. Readiness packs are
introspectable. New executable rules are currently defined internally by
Beacon's registered rule system.

## Current policy example

```yaml
policy:
  waivers:
    - rule_id: kafka.topic.partitions.low
      resource: checkout.retry
      reason: Dev retry topic preserves ordering and is intentionally single-partitioned.
      expires: 2026-12-31
      severity: INFO
```

## What feedback would help?

- Do you need severity overrides, waivers, or full custom rules first?
- Should custom rules be YAML-only, Python plugins, OPA/Rego exports, or pack
  extensions?
- Should policies be global, project-local, environment-specific, or layered?
- How should Beacon show policy exceptions without hiding risk?
- What would make this transparent enough to trust?

## Safe evidence

Paste redacted policy examples, desired rule shapes, or exception workflows.
Please remove secrets, tokens, private hostnames, and production data.
