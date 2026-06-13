# Environment Readiness Technical Guide

This document defines how Beacon can be used as a single readiness gate across
multiple environments, teams, and runtime domains.

It is designed for platform engineers, SRE teams, security engineers, release
managers, and service owners who need deterministic readiness checks before
promotion and controlled diagnostics after deployment.

## 1) Objectives

Beacon readiness should answer:

- Is this environment safe to deploy to right now?
- What high-impact risks block promotion?
- Which risks are acceptable in lower environments but not in production?
- What evidence is missing to make a confident release decision?

Beacon uses deterministic rules and policy overlays to keep release outcomes
consistent across teams.

## 2) Scope and Operating Model

Beacon provides two complementary modes:

- **Readiness mode** (`beacon.cli readiness ...`): pre-deployment confidence and
  environment gating.
- **Diagnostics mode** (`beacon.cli diagnose ...`): incident triage and runtime
  cause narrowing.

Readiness should be used as the promotion contract; diagnostics should be used
for active degradation and post-deploy investigations.

## 3) Readiness Dimensions

A complete environment readiness decision should evaluate these dimensions:

1. **Configuration Safety**
   - Terraform, Kubernetes, Helm, Kafka topic/broker/app settings
2. **Runtime Stability Signals**
   - Lag, latency, retries, disk pressure, rebalance churn, error rates
3. **Data Contract Safety**
   - Schema Registry compatibility, schema evolution risk
4. **Access and Security Posture**
   - ACL guardrails, TLS/mTLS hygiene, auth controls, policy conformance
5. **Operational Survivability**
   - replay-window survivability, retention correctness, blast-radius limits
6. **Release Correlation**
   - deployment event alignment with runtime shifts
7. **Cross-System Flow Health**
   - API -> Kafka -> consumer -> database bottleneck evidence

## 4) Inputs by Domain

Beacon can consume one or many of the following inputs in a single run:

- static infrastructure path (`--static-path`)
- runtime snapshot (`--snapshot`)
- flow snapshot (`--flow`)
- Prometheus collector config (`--prometheus`)
- OpenTelemetry export (`--opentelemetry`)
- Schema Registry collector config (`--schema-registry`)
- Kafka ACL export (`--kafka-acls`)
- Kafka runtime history (`--kafka-history`)
- deployment events (`--deployment-events`)
- optional live Kafka read-only signals (`--kafka-bootstrap-server`)
- optional live Kubernetes read-only signals (`--kubernetes-live`)

Primary all-domain readiness entrypoint:

```bash
python3 -m beacon.cli readiness all \
  --static-path ./examples/supported \
  --snapshot ./examples/supported/runtime/all-runtime.yaml \
  --flow ./examples/runtime/checkout-flow.yaml \
  --prometheus ./examples/supported/prometheus/kafka-jmx-prometheus.yaml \
  --opentelemetry ./examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry ./examples/supported/kafka/schema-registry.yaml \
  --kafka-acls ./examples/supported/kafka/acls.yaml \
  --kafka-history ./examples/supported/kafka/history.yaml \
  --deployment-events ./examples/supported/deployments/events.yaml \
  --environment staging \
  --output json \
  --no-open-report
```

## 5) Environment Profiles

Use `--environment` to apply stricter thresholds by stage:

- `dev`: broad experimentation, low blast radius, warning-heavy
- `test`: integration confidence, stronger contract checks
- `staging`: production-like behavior, strict pre-release gate
- `prod`: strongest gating, minimal tolerance for high-severity risk

Recommended control pattern:

- keep one shared baseline policy
- add environment overlays for exception handling and strictness
- require explicit expiration dates for temporary waivers

## 6) High-Value Use Case Catalog

The following catalog expands Beacon usage beyond a single Kafka check and
supports full environment readiness.

### A. Pre-Deploy Environment Gate (all teams)

**Goal:** Block unsafe promotions before rollout.

- inputs: static config + recent runtime snapshot + deployment events
- pass criteria: no critical blockers, bounded high severity count,
  no unresolved policy violations
- output: readiness score, blocking findings, first actions

### B. Kafka Platform Readiness (streaming teams)

**Goal:** Ensure topic, broker, producer, and consumer safety before high-load
windows.

- checks: replication, ISR risk, lag trends, partition skew, replay risk,
  producer durability/idempotence, consumer group stability
- inputs: Kafka runtime history, ACL export, optional live Kafka metadata

### C. Kubernetes Workload Readiness (service teams)

**Goal:** Detect pod/deployment instability risks before traffic shift.

- checks: resource sizing drift, rollout safety, restart/churn signals,
  namespace-level pressure, deployment instability patterns
- inputs: Kubernetes manifests and optional live Kubernetes collection

### D. Data Contract Release Readiness (data platform)

**Goal:** Prevent incompatible schema evolution from breaking consumers.

- checks: compatibility mode, subject-level drift, topic-subject mapping
- inputs: schema registry collector config + expected topic/subject mapping

### E. API + Consumer + Database Flow Readiness (product teams)

**Goal:** Validate end-to-end path health, not isolated metrics.

- checks: API latency/error trends, consumer lag amplification,
  retry pressure, downstream DB latency correlation
- inputs: flow runtime snapshot + runtime snapshot + deployment events

### F. Security and Access Hygiene Gate (security teams)

**Goal:** Catch environment-specific auth/TLS/ACL weaknesses early.

- checks: ACL overexposure, auth mode drift, certificate hygiene, missing
  hardening settings
- inputs: ACL export + Kafka/Schema Registry access configs

### G. Release Regression Detection (release managers)

**Goal:** Compare pre/post deployment windows to identify regression risk.

- checks: timing correlation between deployment and lag/latency/error shifts
- inputs: deployment events + runtime snapshot/history

### H. DR/Failover Readiness (platform reliability)

**Goal:** Validate survivability before failover drills.

- checks: replication safety, retention/replay windows, dependency bottlenecks,
  control-plane stability
- inputs: static + runtime + Kafka history + flow evidence

### I. Capacity Readiness for Peak Events (business operations)

**Goal:** Prove readiness for expected demand spikes.

- checks: throughput growth trend, disk growth slope, hot partition risk,
  consumer catch-up capacity
- inputs: historical runtime snapshots + Kafka history + flow snapshots

### J. Multi-Cluster / Multi-Tenant Governance

**Goal:** Standardize readiness scoring across business units.

- checks: common policy baseline with tenant-specific overlays
- inputs: per-cluster evidence packs and environment-tagged contexts
- output: comparable scorecards and centralized blocker taxonomy

## 7) Reference Execution Patterns

### Pattern 1: Static-only quick gate

```bash
python3 -m beacon.cli readiness static ./examples/supported \
  --environment test \
  --output json \
  --no-open-report
```

### Pattern 2: Runtime-focused gate

```bash
python3 -m beacon.cli readiness snapshot ./examples/runtime/kafka-runtime.yaml \
  --environment staging \
  --output json \
  --no-open-report
```

### Pattern 3: Full promotion gate

```bash
python3 -m beacon.cli readiness all \
  --static-path ./examples/supported \
  --snapshot ./examples/runtime/kafka-runtime.yaml \
  --kafka-history ./examples/supported/kafka/history.yaml \
  --deployment-events ./examples/supported/deployments/events.yaml \
  --environment prod \
  --output json \
  --no-open-report
```

## 8) Evidence Quality Model

Readiness confidence should scale with evidence completeness:

- **High confidence:** static + runtime + history + deployment timeline
- **Medium confidence:** static + one runtime source
- **Low confidence:** isolated source without timeline or cross-domain context

When evidence is partial, Beacon findings should still be actionable, but final
promotion decisions should require explicit owner approval.

## 9) CI/CD Integration Blueprint

Use Beacon as a release stage in CI/CD:

1. collect environment evidence artifacts
2. run `readiness all` in JSON mode
3. fail pipeline on blocking severities or policy violations
4. archive JSON/HTML artifacts for audit
5. create ticket(s) for non-blocking but high-priority remediation

Example pipeline step:

```bash
python3 -m beacon.cli readiness all \
  --static-path ./infra \
  --snapshot ./artifacts/runtime-snapshot.yaml \
  --flow ./artifacts/flow.yaml \
  --kafka-history ./artifacts/kafka-history.yaml \
  --deployment-events ./artifacts/deployments.yaml \
  --environment prod \
  --output json \
  --no-open-report > readiness-report.json
```

## 10) Operating Standards for Production

- Require `prod` environment profile for production promotions.
- Treat `CRITICAL` findings as automatic blockers.
- Require documented risk acceptance for temporary exceptions.
- Expire waivers automatically and re-evaluate on each release.
- Keep policy and intelligence context versioned with infrastructure code.

## 11) Backlog to Expand "All Environment" Coverage

To make Beacon a broader readiness platform, prioritize these rule-pack
expansions:

- service mesh readiness (timeouts, retries, circuit-breaking defaults)
- ingress/API gateway safety and authentication posture
- database migration readiness and rollback guarantees
- cache consistency and eviction-risk controls
- DNS and certificate lifecycle readiness
- queue/backpressure readiness beyond Kafka
- cloud quota and regional capacity pre-checks
- disaster recovery RTO/RPO policy conformance

## 12) Definition of Done for Environment Readiness

An environment is "ready" when:

- no blocking findings remain for that environment profile
- readiness score meets policy threshold
- evidence confidence is acceptable for release tier
- required runtime and deployment correlation data is present
- remediation owners and timelines exist for non-blocking findings

---

For implementation details, see:

- `docs/ARCHITECTURE.md`
- `docs/MODULE_1_RELEASE.md`
- `docs/MODULE_2_RUNTIME_DIAGNOSTICS.md`
- `docs/MODULE_3_FLOW_INTELLIGENCE.md`


