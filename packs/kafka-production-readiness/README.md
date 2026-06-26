# Kafka Production Readiness Pack

This pack defines the Kafka checks Beacon uses to answer:

```text
Can this Kafka topology and client posture survive production conditions?
```

It is intentionally reviewable. Teams can inspect the rule IDs, compare them
with their own platform standards, and decide where environment-specific
exceptions belong.

## What This Pack Covers

- Topic durability: replication factor, min ISR, retention, compaction, message size
- Broker posture: broker count, internal topic replication, rack awareness, ACL/auth controls
- Client posture: idempotence, acks, compression, offset behavior, TLS/SASL safety
- Consumer behavior: lag, missing offsets, hot partitions, unstable groups, DLQ patterns
- Runtime health: disk pressure, under-replication, controller churn, throttling, queues
- Recovery planning: replay time, retention window, drain capacity
- Schema Registry: unsafe compatibility and missing topic subjects
- Authorization: broad ACLs and missing ACL posture

## Example

```bash
python3 -m beacon.cli packs show kafka-production-readiness
python3 -m beacon.cli packs rules kafka-production-readiness
python3 -m beacon.cli readiness static examples/product-readiness/distributed-infra-risk --environment prod --no-html --no-open-report
```

## Relationship To OPA/Sentinel

OPA/Sentinel are ideal for hard policy enforcement:

```text
Deny this deployment if replication_factor < 3.
```

Beacon uses this pack for release-readiness interpretation:

```text
Replication risk, missing owner metadata, weak client security, and unsafe
Schema Registry compatibility combine into a production-readiness concern.
Fix these first.
```

