# Beacon SSD

This is the product spec Beacon should keep if it is being built as a real
company: not a side project, not a toy AI tool, and not another generic scanner.

Current implementation status is tracked in
[`BEACON_SSD_GAP_ANALYSIS.md`](BEACON_SSD_GAP_ANALYSIS.md).

Beacon is a production-readiness and operational intelligence platform for
distributed systems.

## Product Motto

```text
Run Beacon before production.
Ask Beacon why the system is degrading.
```

Beacon helps engineering teams answer one hard question:

```text
Is this distributed system safe enough to run in production, and if not,
what should we fix first?
```

## Product Identity

Beacon provides production-readiness and operational intelligence for
distributed systems.

It helps engineering organizations:

- detect operational risk before production incidents
- diagnose runtime degradation during incidents
- recommend operational decisions during recovery
- continuously evaluate infrastructure survivability

Beacon is not a dashboard, log platform, or generic AI chatbot. Beacon is the
operational reasoning layer.

## Core Problem

Modern engineering teams already have:

- monitoring
- logs
- dashboards
- alerts
- metrics
- policy-as-code
- cloud and Kubernetes tooling

But they still struggle to answer:

- Why is the system degrading?
- What changed?
- What is the real bottleneck?
- What should we do first?
- Is this architecture production ready?

Beacon turns infrastructure configs, runtime signals, ownership metadata,
topology, and operational context into deterministic readiness decisions,
incident diagnoses, and next operational actions.

## Adoption Principles

Beacon must be:

- easy to try
- transparent
- locally runnable
- useful in 5 minutes
- clear that it does not replace existing tools

Beacon should feel like:

```text
Run this before production and see what might break.
```

Not:

```text
Trust this black-box DevOps AI platform.
```

## What Beacon Is Not

Beacon must not become:

- generic observability platform
- dashboard-heavy monitoring tool
- telemetry storage engine
- log ingestion platform
- AI for DevOps chatbot
- OPA or Sentinel replacement
- auto-remediation system

Beacon complements existing tools:

```text
OPA/Sentinel enforce individual policies.
Prometheus/Grafana observe runtime metrics.
Beacon explains release readiness and operational risk across many signals.
```

## Core Product Rule

```text
Deterministic intelligence first.
AI explanation second.
```

This is non-negotiable because infrastructure tooling must be explainable.
Enterprises trust deterministic findings. AI hallucinations destroy
infrastructure trust.

AI may explain, summarize, or help navigate Beacon output later, but the
readiness decision must come from deterministic evidence.

## Product Modules

Beacon evolves into five major modules.

## Module 1: Production Readiness Intelligence

Goal:

```text
Prevent production incidents before deployment.
```

Inputs:

- Terraform
- Terraform plan/state JSON
- cloud inventory exports
- Helm charts
- Kubernetes YAML
- Kafka configs
- cloud configs
- IAM/storage/database configs
- CI/CD deployment manifests
- architecture and topology metadata

Outputs:

- production readiness score
- production decision
- scalability risk analysis
- resiliency assessment
- operational risk report
- blast-radius estimation
- deployment safety recommendations
- HTML/JSON report

### Use Case 1: Can This Kafka Topology Survive Broker Failure?

Problem:

- replication factor 1
- weak ISR
- poor retention settings
- missing rack awareness
- unsafe replica placement

Beacon detects:

- high recovery risk
- possible data loss
- replay instability
- single-failure-domain risk

Business value:

```text
Prevents production outages and data-loss scenarios before deployment.
```

### Use Case 2: Can This Architecture Scale During Traffic Spikes?

Problem:

- low partition count
- insufficient autoscaling
- unsafe consumer concurrency
- missing HPA headroom
- unbounded pods
- weak downstream capacity signals

Beacon detects:

- scaling bottlenecks
- partition parallelism risk
- operational saturation risk
- Kubernetes workload capacity risk

Business value:

```text
Prevents peak-load failures and blind over-scaling.
```

### Use Case 3: Is This Deployment Operationally Safe?

Problem:

- unsafe retries
- missing probes
- weak resiliency
- broad IAM
- permissive Kubernetes admission/RBAC
- unsafe CI/CD release controls

Beacon detects:

- operational anti-patterns
- recovery instability
- deployment blast radius
- release safety gaps

Business value:

```text
Reduces deployment-induced incidents.
```

### Use Case 3A: What Cloud Resources Exist Outside Terraform State?

Problem:

- resources created manually during incidents
- old experiments nobody owns
- dormant account workloads
- production cloud resources missing from Terraform state
- resources with cost activity but no owner or lifecycle record

Beacon compares:

- cloud inventory export
- Terraform state JSON
- ownership metadata
- optional cost/activity context
- optional network/security posture

Beacon detects:

- unmanaged cloud resources
- missing owner/application tags
- unknown blast radius
- unknown-after-apply Terraform values that reduce pre-release correlation confidence
- unmanaged public exposure
- unmanaged data or search infrastructure
- resources that should be imported, deleted, tagged, quarantined, or reviewed

Business value:

```text
Improves cloud estate hygiene and prevents hidden unmanaged infrastructure from
becoming a production, security, cost, or recovery risk.
```

Important readiness rule:

```text
Pre-apply scans are intent-based.
Post-apply scans are evidence-confirmed.
```

If Terraform plan values such as endpoints, subnet IDs, broker addresses,
resource IDs, DNS names, or service URLs are unknown until apply, Beacon must
not invent strong dependency edges. It should mark those correlations as low
confidence and recommend stable mapping keys such as tags, Kubernetes labels,
Kafka topic names, Backstage refs, Terraform state, or live snapshots.

Important distinction:

```text
Terraform drift detection asks:
"Did a managed resource change outside Terraform?"

Beacon IaC coverage asks:
"What important cloud resources exist outside Terraform entirely, and what risk
do they create?"
```

## Module 2: Runtime Operational Diagnostics

Goal:

```text
Diagnose why runtime degradation is happening.
```

Initial deep domain:

```text
Kafka operational intelligence.
```

Kafka is the right early wedge because it is operationally painful, complex,
weakly served by current tooling, and creates a strong expertise moat.

### Use Case 4: Why Is Kafka Consumer Lag Increasing?

Beacon analyzes:

- consumer lag
- partition imbalance
- throughput mismatch
- retention pressure
- consumer topology
- broker health
- producer stability
- downstream runtime signals where available

Example output:

```text
Likely cause: Consumer-side DB bottleneck
Confidence: High

Evidence:
- broker healthy
- lag concentrated on consumer
- producer stable
- partition distribution balanced

Recommendation:
Investigate downstream DB latency and retry amplification.
```

Business value:

```text
Reduces MTTR dramatically.
```

### Use Case 5: Should We Scale Kafka Or Optimize Consumers?

Problem:

Disk usage crosses 80 percent and teams often panic-scale infrastructure.

Beacon analyzes:

- message growth
- retention
- lag
- producer throughput
- cleanup policy
- payload-size growth
- broker disk skew

Example output:

```text
Storage growth is primarily caused by:
- retention misconfiguration
- increased producer payload size

Expanding brokers alone will not solve long-term growth.
```

Business value:

```text
Reduces infrastructure cost waste.
```

### Use Case 6: Why Is One Partition Overloaded?

Beacon detects:

- partition skew
- hot keys
- uneven producer distribution
- lag concentrated on a small number of partitions

Recommendation:

```text
Review producer partition key strategy.
Consumer scaling alone may not solve skew-related lag.
```

Business value:

```text
Prevents persistent scaling inefficiency.
```

### Use Case 7: Why Are Consumers Unstable?

Beacon detects:

- rebalance storms
- heartbeat mismatch
- deployment churn
- session timeout instability
- max poll interval risk
- member churn

Business value:

```text
Stabilizes high-throughput distributed systems.
```

## Module 3: Flow Intelligence

Goal:

```text
Understand operational bottlenecks across services, Kafka, databases,
APIs, Kubernetes, storage, and deployments.
```

This is Beacon's bigger differentiator after Kafka runtime intelligence.

### Use Case 8: Where Is The Bottleneck?

Example flow:

```text
API
↓
Kafka Producer
↓
Kafka Topic
↓
Consumer
↓
Database
```

Beacon detects:

- Kafka healthy
- consumer lag increasing
- DB latency increased

Beacon outputs:

```text
Likely downstream DB bottleneck causing consumer slowdown.
```

Business value:

```text
Eliminates manual cross-system investigation.
```

### Use Case 9: Did Deployment Trigger Degradation?

Beacon correlates:

- deployment timeline
- lag growth
- latency spikes
- error growth
- retry pressure

Business value:

```text
Reduces rollback decision time.
```

### Use Case 10: Why Is Latency Cascading Across Systems?

Beacon detects:

```text
API timeout
↓
consumer retries
↓
Kafka lag growth
↓
storage pressure
```

Business value:

```text
Explains cascading operational failures.
```

## Module 4: Operational Decision Intelligence

Goal:

```text
Recommend what engineers should actually do.
```

This is critical because raw findings are not enough during production review or
incident recovery.

Current implementation direction:

- deterministic ranked decisions are generated from grouped findings
- each decision carries a target domain, safety level, confidence, evidence, and
  "do not do" guidance
- readiness, runtime, and flow-derived decision ranking are supported
- flow bottleneck rankings can now become operational decisions with source
  findings, evidence required, and anti-actions such as "do not scale Kafka
  before validating downstream database pressure"

### Use Case 11: What Should We Scale First?

Beacon recommends where action should begin:

- partitions
- consumers
- storage
- DB pool
- API capacity
- retries
- producer throttling
- rollback

Instead of:

```text
Scale everything blindly.
```

### Use Case 12: What Is The Safest Operational Action?

Beacon prioritizes:

- rollback
- retention optimization
- rebalance mitigation
- producer throttling
- safe scaling
- downstream dependency investigation

## Module 5: Predictive Operational Intelligence

Goal:

```text
Predict operational degradation, failure risk, scaling risk, replay risk,
and deployment instability.
```

This is the long-term moat.

### Use Case 13: Will This Cluster Hit Storage Saturation?

Beacon predicts:

- growth trajectory
- retention exhaustion
- replay amplification
- disk skew

### Use Case 14: Will This Deployment Destabilize Consumers?

Beacon predicts:

- rebalance amplification
- startup overload
- partition imbalance risk
- downstream retry pressure

## Final Product Experience

Before production, Beacon answers:

```text
Is this architecture operationally safe?
```

During production, Beacon answers:

```text
Why is the system degrading?
```

During incident recovery, Beacon answers:

```text
What should engineers do first?
```

## Enterprise Architecture

```text
                   ┌────────────────────────┐
                   │ Infrastructure Configs │
                   └────────────┬───────────┘
                                │
                   ┌────────────▼───────────┐
                   │ Production Readiness   │
                   │ Intelligence Engine    │
                   └────────────┬───────────┘
                                │

────────────────────────────────┼────────────────────────────────

Kafka Runtime           Kubernetes Runtime           Cloud Runtime
Collectors              Collectors                    Collectors

────────────────────────────────┼────────────────────────────────
                                ▼

                   ┌────────────────────────┐
                   │ Operational Correlation│
                   │ Engine                 │
                   └────────────┬───────────┘
                                ▼

                   ┌────────────────────────┐
                   │ Root Cause Intelligence│
                   │ Engine                 │
                   └────────────┬───────────┘
                                ▼

                   ┌────────────────────────┐
                   │ Operational Decision   │
                   │ Engine                 │
                   └────────────┬───────────┘
                                ▼

                   ┌────────────────────────┐
                   │ AI Explanation Layer   │
                   │ + Reporting            │
                   └────────────────────────┘
```

## Internal Architecture Direction

Target long-term shape:

```text
beacon/
├── scan/
├── diagnose/
│   ├── kafka/
│   ├── kubernetes/
│   ├── storage/
│   ├── database/
│   └── flow/
├── collectors/
├── analyzers/
├── findings/
├── decisions/
├── topology/
├── patterns/
├── correlations/
├── scoring/
├── ai/
└── reporting/
```

Current implementation can evolve gradually toward this. Do not perform a large
architecture rewrite just for folder aesthetics. Preserve working behavior,
tests, and release confidence.

## Readiness Packs

Beacon should expose checks as inspectable packs.

Current first pack:

```text
kafka-production-readiness
```

Future packs:

- iac-coverage-readiness
- cloud-production-readiness
- cloud-aws-readiness
- cloud-azure-readiness
- cloud-gcp-readiness
- iam-readiness
- cicd-release-readiness
- distributed-system-readiness

Each pack should include:

- rule IDs
- intent
- severity
- recommendation
- examples
- non-goals

This makes Beacon easier to trust and easier to debate.

## Go-To-Market Strategy

Initial wedge:

```text
Production readiness first.
Kafka operational intelligence as the deep expert wedge.
```

Expansion path:

```text
Kafka
↓
Flow diagnostics
↓
Deployment intelligence
↓
Kubernetes operational intelligence
↓
Distributed operational intelligence
```

The first user promise must stay simple:

```text
Run Beacon locally in 5 minutes and get a production-readiness report.
```

## Market Positioning

Best short description:

```text
Beacon helps engineering teams detect production-readiness risks before release
and diagnose runtime degradation across distributed systems using deterministic
operational intelligence.
```

Best 30-second pitch:

```text
Beacon is a production-readiness and operational intelligence platform for
distributed systems. It scans infrastructure configs, Kafka settings,
Kubernetes manifests, cloud/IAM/storage posture, runtime snapshots, and flow
signals. Instead of giving teams another dashboard, Beacon gives a decision:
is this production ready, why not, what is the likely root cause, and what
should engineers do first.
```

## Demo Commands

Run the full project demo:

```bash
scripts/demo_project.sh
```

Generated artifacts:

```text
reports/project-demo/
```

Run Module 1 readiness:

```bash
python3 -m beacon.cli readiness static examples/supported \
  --environment prod \
  --context examples/supported/intelligence/context.yaml \
  --no-open-report
```

Run environment-aware dev readiness:

```bash
python3 -m beacon.cli readiness static examples/bad-infra \
  --environment dev \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report
```

Run Kafka quota/throttling incident:

```bash
python3 -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/quota-throttle-runtime.yaml \
  --no-open-report
```

Run Kafka rebalance storm incident:

```bash
python3 -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml \
  --no-html \
  --no-open-report
```

Run flow intelligence:

```bash
python3 -m beacon.cli diagnose flow \
  examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report
```

Run all-domain diagnostic bundle:

```bash
python3 -m beacon.cli diagnose all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --flow examples/supported/runtime/flow-runtime.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --kafka-acls examples/supported/kafka/acls.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report
```

Inspect readiness packs:

```bash
python3 -m beacon.cli packs list
python3 -m beacon.cli packs show kafka-production-readiness
python3 -m beacon.cli packs rules kafka-production-readiness
```

## Near-Term Next Steps

1. Keep Module 1 release-shaped.
   - Make the first 5-minute readiness demo excellent.
   - Improve report clarity and top-risk grouping.
   - Keep Docker-first sharing clean.

2. Keep readiness packs visible.
   - Kafka pack is first.
   - Add Kubernetes, cloud, and provider-specific Terraform/cloud packs next.
   - Let users suggest, challenge, and adapt checks.

3. Improve signal quality.
   - Reduce noisy repeated findings.
   - Improve environment-aware severity.
   - Keep raw findings below grouped root causes.

4. Deepen Module 2 Kafka diagnostics.
   - Keep Kafka runtime as the expert wedge.
   - Focus on lag, rebalance, hot partitions, storage pressure, quotas, ACLs,
     schema risk, and replay readiness.

5. Strengthen Module 3 flow intelligence.
   - Rank bottlenecks across API, Kafka, consumers, database, storage, and
     deployments.

## Success Metrics

Short-term:

- 10 engineers try Beacon locally
- 3 people open feedback issues
- 1 person says Beacon found something useful

Medium-term:

- teams run Beacon in CI before release
- teams inspect and customize readiness packs
- platform teams use Beacon reports during release review

Long-term:

```text
Run Beacon before production.
Ask Beacon why the system is degrading.
```

## Final Product Moat

Beacon's moat is not dashboards, AI, or scanning.

Beacon's moat is:

```text
encoded operational reasoning.
```

That becomes hard to copy, valuable, enterprise-trustworthy, and operationally
differentiated.
