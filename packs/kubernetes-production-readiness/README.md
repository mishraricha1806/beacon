# Kubernetes Production Readiness Pack

This pack defines the Kubernetes checks Beacon uses to answer:

```text
Can this Kubernetes workload and cluster posture survive production conditions?
```

It is intentionally reviewable. Teams can inspect the rule IDs, compare them
with platform standards, and decide where environment-specific exceptions
belong.

## What This Pack Covers

- Workload availability: replicas, probes, PDBs, topology spread
- Capacity safety: requests/limits, HPA headroom, Pending pods, node pressure
- Security posture: privileged containers, host namespaces, non-root runtime,
  privilege escalation, seccomp, read-only root filesystem
- Cluster guardrails: Pod Security Standards, NetworkPolicy, RBAC, admission
  webhook failure policy
- Secret hygiene: inline Kubernetes Secret material
- Runtime health: NotReady nodes, crash loops, unavailable deployments

## Example

```bash
python3 -m beacon.cli packs show kubernetes-production-readiness
python3 -m beacon.cli packs rules kubernetes-production-readiness
python3 -m beacon.cli readiness static examples/product-readiness/distributed-infra-risk --environment prod --no-html --no-open-report
```

## Relationship To OPA/Gatekeeper/Kyverno

OPA Gatekeeper and Kyverno are ideal for admission-time enforcement:

```text
Deny this pod if privileged = true.
```

Beacon uses this pack for release-readiness interpretation:

```text
Missing probes, weak disruption protection, permissive RBAC, fail-open
admission webhooks, and runtime pod instability combine into a production
readiness concern.
```

