# Distributed System Production Readiness Pack

This is Beacon's cross-domain pack. It answers the product question:

```text
Can this distributed system safely go to production?
```

It does not replace the domain packs. Instead, it pulls the most release
significant signals from Kafka, Kubernetes, cloud, IaC coverage, CI/CD,
topology, and flow diagnostics into one inspectable readiness surface.

## What This Pack Covers

- Kafka broker-failure survivability, write durability, retention, lag, and schema safety
- Kubernetes workload health, availability, admission control, and RBAC posture
- Cloud network, managed database, identity, object-storage, quota, and provider-specific posture
- IaC coverage for unmanaged resources outside Terraform state
- CI/CD deployment safety and supply-chain controls
- Service topology ownership, criticality, and blast radius
- Flow signals such as downstream database bottlenecks and deployment-correlated degradation

## How To Inspect It

```bash
python3 -m beacon.cli packs show distributed-system-production-readiness
python3 -m beacon.cli packs rules distributed-system-production-readiness
```

## How To Use It

Run Beacon across the full supported example set:

```bash
python3 -m beacon.cli readiness all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --flow examples/supported/runtime/flow-runtime.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --kafka-acls examples/supported/kafka/acls.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

## Scope

This pack is a release-readiness grouping, not a policy enforcement layer. OPA,
Sentinel, admission controllers, and cloud-native policy tools remain the right
place for hard allow/deny controls. Beacon uses this pack to explain production
readiness, rank risk, and show what engineers should fix first.
