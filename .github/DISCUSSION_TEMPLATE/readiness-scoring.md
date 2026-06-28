---
name: Readiness scoring and decision synthesis
about: Discuss how Beacon should combine Kafka, runtime, and capacity signals into one release decision
title: "How should Beacon combine replication, lag, and disk pressure into one readiness decision?"
labels: readiness-scoring, product-feedback
---

## Question

How should Beacon combine Kafka replication factors, consumer lag, broker disk
pressure, and related runtime signals into one production-readiness decision?

## Current implementation areas

- `beacon/engine/rule_direction.py`
- `beacon/readiness/interpretation.py`

These files contain the current severity synthesis and interpretation logic.

## What feedback would help?

- Which signals should block production in `prod`?
- Which signals should be downgraded in `dev` or `test`?
- When should repeated topic-level findings be grouped into one root cause?
- How should Beacon avoid over-counting derivative findings?
- What should the score mean when one root cause affects many resources?

## Example scenario

```text
Kafka cluster:
- broker count: 1
- many topics have replication.factor=1
- consumer lag is low
- disk pressure is normal

Should Beacon return NOT READY, READY_WITH_RISK, or a dev-only warning?
```

## Safe evidence

Paste redacted findings, scoring examples, or synthetic configs. Please remove
secrets, tokens, private hostnames, and production data.
