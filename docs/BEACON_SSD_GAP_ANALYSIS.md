# Beacon SSD Gap Analysis

This compares the current repository against `docs/BEACON_SSD.md`.

Generated from the current local repository state.

## Current Position

Beacon is no longer just a static scanner. The repository now has the backbone
of the SSD:

```text
scanner / connectors
→ normalizers
→ registered rules + metadata
→ evaluator
→ readiness scoring
→ diagnostics
→ correlations
→ reports / UI / JSON
→ ranked operational decisions
→ readiness packs
```

Current verified coverage:

```text
registered rules: 145
metadata entries: 291
readiness packs: 8
Kafka pack rules: 90
```

Release gates currently pass:

```text
Module 1 release gate
Module 2 diagnostic gate
Module 3 flow gate
Full pytest suite
```

## SSD Module Status

| SSD Module | Current Status | Repo Evidence | Product Assessment |
| --- | --- | --- | --- |
| Module 1: Production Readiness Intelligence | Strong RC foundation | `beacon/readiness/`, `beacon/scanner.py`, `beacon/rules/*_registered_rules.py`, `examples/product-readiness/`, `scripts/module1_release_check.py` | Closest to release. Keep polishing instead of adding broad scope. |
| Module 2: Runtime Operational Diagnostics | Active and useful, Kafka-first | `beacon/kafka_runtime_connector.py`, `beacon/runtime_advisor.py`, `beacon/diagnose/`, `examples/supported/kafka/scenarios/`, `scripts/module2_diagnostic_check.py` | Good wedge. Needs more real-world evidence quality and live-cluster ergonomics. |
| Module 3: Flow Intelligence | Early but real | `beacon/flow_runtime.py`, `beacon/opentelemetry_connector.py`, `beacon/diagnose/flow_ranker.py`, `beacon/correlations/root_cause.py`, `scripts/module3_flow_check.py` | Promising differentiator. Flow rankings now carry owner, criticality, affected services, business impact, blast radius, and incident priority. OpenTelemetry exports can infer API/Kafka/database flow components from spans. Needs richer live topology and service-catalog context. |
| Module 4: Operational Decision Intelligence | Started and first-class | `beacon/decisions/decision_engine.py`, `beacon/readiness/kafka/readiness_engine.py`, `beacon/readiness/readiness_reporter.py`, JSON formatter, UI renderer | Ranked decisions now include action, target, disposition, safety, confidence, evidence, and "do not do" guidance. Kubernetes, database recovery, IaC review, and monitor/no-urgent-action decisions now have explicit playbooks. |
| Module 5: Predictive Operational Intelligence | Not implemented | docs only | Correctly deferred. Do not start until Modules 1-3 have user validation. |

## Adoption Principle Status

| Principle | Status | Notes |
| --- | --- | --- |
| Easy to try | Good | Docker, UI, CLI, examples, demo scripts exist. README is long but practical. |
| Transparent | Improving | Kafka readiness pack and OPA/Sentinel positioning exist. Need more packs. |
| Locally runnable | Good | Local CLI/UI and Docker-first path exist. Runtime connectors are read-only. |
| Useful in 5 minutes | Medium | Examples exist, but first-run path still needs simplification and cleaner demo flow. |
| Does not replace existing tools | Good | `docs/BEACON_VS_OPA_SENTINEL.md` and README explain complement positioning. |

## Where Beacon Is Strong Now

### 1. Module 1 Readiness Engine

Beacon has real deterministic readiness coverage across:

- Kafka configs and runtime-style signals
- Kubernetes manifests and runtime snapshots
- Terraform HCL, plan JSON, and state JSON
- Helm rendered manifests
- object storage
- IAM
- cloud database/network posture
- CI/CD workflow risk
- topology/blast-radius signals
- environment-aware scoring
- evidence and release comparison

This is the strongest near-term product.

### 2. Kafka Depth

Kafka is clearly the deepest domain:

- topic durability
- broker safety
- ISR / under-replication / offline partitions
- retention and replay
- producer and consumer config
- lag, rebalance, hot partition, churn
- Schema Registry
- ACLs
- runtime history
- quotas/throttling
- payload/storage pressure
- readiness pack

This supports the SSD wedge.

### 3. Deterministic Root-Cause Direction

Beacon already has deterministic hypotheses for:

- downstream database bottleneck
- deployment regression
- retry cascade
- storage/capacity pressure
- Kafka single-broker topology
- schema governance
- payload storage growth
- Kubernetes workload instability

This is the right moat direction.

### 4. Trust Layer

Beacon now has:

- inspectable Kafka readiness pack
- rule metadata catalog
- issue templates for feedback
- OPA/Sentinel complement doc
- local-first Docker/CLI/UI path

This directly addresses market trust concerns.

## Main Gaps Against SSD

### Gap 1: First Five-Minute Experience Is Still Too Heavy

Beacon is powerful, but the README and command surface can feel large.

Needed:

- one default demo path
- one expected screenshot/output
- one command for UI
- one command for CLI
- one feedback link

Current quickstart artifact:

- `QUICKSTART_5_MINUTES.md`

Success target:

```text
New user runs Beacon and understands the result in under 5 minutes.
```

### Gap 2: Cloud Provider Parity Is Not Complete Yet

SSD says Beacon should support distributed-system readiness across cloud
providers, not just AWS.

Current:

```text
kafka-production-readiness
kubernetes-production-readiness
cloud-production-readiness
cloud-azure-readiness
cloud-gcp-readiness
terraform-aws-readiness
iac-coverage-readiness
distributed-system-production-readiness
```

The cloud-facing product pack now exists, and Azure/GCP provider packs are
visible. Provider-specific evidence is still deepest for AWS; Azure/GCP now
cover managed database basics, deletion-protection evidence, customer-managed
encryption-key evidence, Key Vault/private endpoint posture, Azure VM scale-set
headroom, Azure/GCP quota headroom, GCP firewall/GKE posture, plus storage/IAM
posture.

Missing next provider depth:

- deeper Azure regional resiliency checks across resource groups/subscriptions
- deeper GCP private connectivity and regional dependency checks

### Gap 3: IaC Coverage Readiness Needs More Provider Depth

The SSD includes unmanaged cloud resource detection.

Current:

- documented in `docs/IAC_COVERAGE_READINESS.md`
- implemented as file-based `readiness iac-coverage`
- example files exist under `examples/iac-coverage/`
- supports Beacon `resources`, AWS Config `configurationItems`, AWS Resource
  Explorer-style `Resources`, and Steampipe/CloudQuery-style `rows`
- Terraform plan unknown-after-apply values now produce explicit low-confidence
  correlation-gap findings instead of fake dependency certainty

Next expansion should support more provider-specific semantics:

```text
Azure Resource Graph / GCP Cloud Asset Inventory / provider-specific ownership,
network, database, and identity fields
```

### Gap 4: Module 4 Decision Intelligence Needs More Scenario Depth

Beacon now has first-class ranked operational decisions in readiness summaries,
console output, and JSON output.
Runtime flow bottleneck rankings can also generate operational decisions with
source-finding provenance, missing evidence, and explicit anti-actions.
The decision engine now includes explicit playbooks for rollback-before-scale,
Kafka client throttling before broker expansion, and retention cleanup before
storage expansion.

Current decision fields include:

- rank
- action
- disposition
- priority score
- target
- safety
- confidence
- why
- evidence
- evidence required
- do_not_do
- source rule IDs
- source findings

Remaining work:

- add more incident-specific templates
- add more domain-specific decisions beyond the first Kubernetes, cloud database, IaC coverage, and flow-bottleneck playbooks
- add "scale vs rollback vs investigate downstream" examples to demos

### Gap 5: Module 3 Needs More Live Topology Context

Flow intelligence exists, but for enterprise usefulness it needs stronger
service/dependency context.

Implemented:

- owner/team/criticality propagation
- business-flow blast-radius mapping
- incident priority per ranked flow bottleneck
- HTML/UI display of flow owner, criticality, business impact, and affected services
- OpenTelemetry span-to-flow component mapping
- visual flow path panel with bottleneck highlighting
- evidence-used, evidence-missing, and inspect-next panels for every visible flow path node
- source-finding provenance and HTML drilldowns for every visible flow path node
- time-window severity tuning by deployment environment and service criticality
- service topology and Backstage catalog context import for owner, criticality, business impact, and blast radius
- richer service-name matching across Backstage refs, namespaces, aliases, dotted names, and common runtime suffixes
- organization-specific service matching aliases through intelligence context
- organization-specific glob service matching patterns through intelligence context

Needed:

- deployment window correlation across more domains
- live topology discovery adapters for service catalogs

### Gap 6: Predictive Intelligence Should Stay Deferred

Module 5 is not implemented. That is correct for now.

Do not start prediction until:

- Module 1 has user validation
- Module 2 Kafka incident diagnostics are trusted
- Module 3 flow ranking is stable
- Beacon has enough historical evidence inputs

## Recommended Next Work

Do these in order.

## Step 1: Polish The First Five-Minute Experience

Goal:

```text
Make the public product easier to try than it is today.
```

Actions:

- Add a short `QUICKSTART.md` or shorten the README top path.
- Make "Try Beacon in 5 minutes" the first user journey.
- Include exact Docker UI and Docker CLI commands.
- Include expected result for `examples/product-readiness/distributed-infra-risk`.
- Link directly to GitHub issue templates.

Why first:

```text
Adoption matters more than adding another rule right now.
```

## Step 2: Deepen Operational Decisions

Goal:

```text
Move from basic ranked decisions to richer operational playbooks.
```

Structured decision output now exists:

```text
action
rank
safety
target
why
evidence
do_not_do
```

Example:

```text
1. Investigate DB latency before scaling Kafka
2. Reduce producer payload size before adding brokers
3. Roll back deployment if degradation started within deployment window
```

Why second:

```text
This is the bridge from "scanner" to "operational reasoning platform."
```

## Step 3: Deepen Azure And GCP Cloud Readiness

Goal:

```text
Move Azure and GCP from current production-readiness coverage toward broader
provider parity.
```

Current Azure/GCP rules now include managed database network exposure, backup,
HA basics, deletion-protection evidence, customer-managed encryption-key
evidence, Key Vault/private endpoint posture, Azure VM scale-set headroom,
Azure/GCP quota headroom, GCP firewall/GKE posture, storage, and IAM.

Next rules should include:

- Azure subscription and resource-group regional resiliency posture
- GCP private connectivity posture beyond firewall and GKE control-plane checks
- provider-specific evidence mapping for approved exceptions and policy context

Why third:

```text
This keeps Beacon's cloud story aligned with the SSD and avoids AWS-only product
positioning.
```

## Step 4: Deepen Distributed-System Readiness

Goal:

```text
Move from a cross-domain rule pack to richer distributed-system reasoning.
```

Add:

- service criticality and owner propagation into release blockers (implemented in distributed readiness summary)
- accepted exception candidates with required evidence (implemented for non-critical findings with approved-exception language)
- explicit "fix before rollout" vs "monitor" disposition (implemented in operational decisions and distributed blockers)
- distributed-system pack examples in the 5-minute demo

Why fourth:

```text
This makes Beacon answer the product question more directly: can this
distributed system go to production?
```

## Step 5: Deepen Module 3 Flow Intelligence

Goal:

```text
Turn flow examples into a richer cross-system reasoning model.
```

Add:

- service topology pack/examples
- business flow criticality
- owner propagation
- deployment-to-flow correlation
- blast-radius summary per flow

Why fifth:

```text
This is Beacon's long-term differentiator, but it needs the readiness foundation first.
```

## Current Verdict

Beacon is aligned with the SSD.

Best summary:

```text
Module 1 is release-candidate quality.
Module 2 is active and Kafka-first, with real incident scenarios.
Module 3 exists and proves the flow-intelligence direction.
Module 4 has started as first-class structured decision intelligence.
Module 5 is intentionally future.
```

The next best move is not "more random rules."

The next best move is:

```text
1. polish the 5-minute public experience
2. deepen operational decisions with more real incident scenarios
3. deepen distributed-system readiness with business criticality and disposition
```
