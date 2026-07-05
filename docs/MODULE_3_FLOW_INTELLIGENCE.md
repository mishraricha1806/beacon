# Module 3 Flow Intelligence

Module 3 is Beacon's cross-system flow intelligence layer.

Module 1 answers:

- Is this system production ready before rollout?

Module 2 answers:

- Why is Kafka or a runtime domain degrading?

Module 3 answers:

- Where is the bottleneck across API, Kafka, consumers, databases, storage, Kubernetes, and deployments?
- Did a deployment trigger degradation?
- Is latency cascading across dependent systems?

## Current Scope

Module 3 is currently deterministic and snapshot-driven. It does not discover a
full live service graph yet.

Supported inputs:

- Flow runtime snapshots
- Combined runtime snapshots
- Kafka history snapshots
- Deployment event YAML/JSON
- OpenTelemetry-derived flow signals and span-inferred flow components
- Prometheus-derived runtime signals
- Service topology YAML and Backstage `catalog-info.yaml` component metadata

Current flow playbooks:

- `module3.flow.bottleneck`
- `module3.flow.deployment_triggered`
- `module3.flow.cascading_latency`

Current diagnostic output:

- `flow_bottleneck_rankings`
- `deployment_window_analyses`

Each flow ranking includes:

- `flow`
- `owner`
- `criticality`
- `business_impact`
- `affected_services`
- `incident_priority`
- `flow_path`
- `top_bottleneck`
- `top_confidence`
- ranked components with component type, confidence, status, reason, matched evidence,
  evidence used, evidence missing, inspect-next guidance, and source-finding
  provenance

OpenTelemetry exports can infer flow components from spans when explicit
`flow.components` are not provided. Beacon maps API, Kafka producer/consumer,
and database spans into flow components, derives unhealthy component signals
from error/timeout/latency evidence, and carries flow owner/criticality/blast
radius context into the ranked diagnosis.

Topology/service-catalog style inputs can provide owner, criticality,
business impact, aliases, dependents, and blast-radius context. When an
all-domain diagnosis includes topology findings and runtime flow findings,
Beacon imports matching service context into the flow ranking so runtime
snapshots do not need to repeat ownership and business-impact metadata.
Backstage `Component` entities are supported as a file-based adapter: Beacon
maps `spec.owner`, `spec.dependsOn`, `spec.dependencyOf`, and `beacon.io/*`
annotations into the same topology service model.
Service matching handles common catalog/runtime naming differences, including
Backstage refs such as `component:default/checkout`, namespace-prefixed names
such as `payments/checkout-api`, dotted names, and runtime suffixes such as
`-api`, `-consumer`, `-worker`, and `-service`.
When defaults are not enough, organization intelligence context can define
explicit service aliases:

```yaml
service_matching:
  aliases:
    checkout:
      - claim-intake-edge
      - member-enrollment-flow
  patterns:
    claims-*-consumer: claims-platform
```

`diagnose all` accepts the same context file with `--context`.

HTML and UI reports render a visual flow path from ranked components, ordered
by operational flow stage, and mark the current bottleneck directly in the path.
Reports also show evidence-used, evidence-missing, and inspect-next panels for
each visible flow-path node so engineers can see why Beacon ranked every stage
and what additional signal would strengthen the diagnosis. Each visible node
also carries source-finding drilldowns with rule ID, severity, title, and file
context; HTML reports link those source findings back to the detailed finding
section for auditability.

Each deployment window analysis includes:

- service
- version
- deployment timestamp
- before/after metrics
- delta and ratio
- severity and matched rule

Deployment correlation also records match evidence:

- service
- namespace
- environment
- criticality
- changed components
- matched finding count
- whether before/after window metrics were present

Before/after deployment window analysis now reports both original rule severity
and tuned severity. Tuning considers the deployment environment and service
criticality so a production critical checkout regression can be escalated while
a similar non-production low-criticality signal remains a review item.

Current root-cause correlations:

- `correlation.root_cause.downstream_database_bottleneck`
- `correlation.root_cause.deployment_regression`
- `correlation.root_cause.retry_cascade`
- `correlation.root_cause.storage_capacity_pressure`
- `correlation.root_cause.kubernetes_workload_instability`

## Example Commands

```bash
python3 -m beacon.cli diagnose flow \
  examples/supported/flow/scenarios/downstream-db-bottleneck.yaml \
  --no-html \
  --no-open-report

python3 -m beacon.cli diagnose flow \
  examples/supported/flow/scenarios/deployment-triggered-degradation.yaml \
  --no-html \
  --no-open-report

python3 -m beacon.cli diagnose flow \
  examples/supported/flow/scenarios/cascading-latency.yaml \
  --no-html \
  --no-open-report
```

All-domain flow diagnosis:

```bash
python3 -m beacon.cli diagnose all \
  --static-path examples/supported/backstage \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --no-html \
  --no-open-report
```

## Release Gate

Run:

```bash
python3 scripts/module3_flow_check.py
```

The gate verifies:

- Flow plus database evidence ranks downstream database bottleneck.
- Deployment-correlated flow degradation maps to the deployment-triggered playbook.
- API timeouts plus retries plus Kafka lag rank retry cascade.
- Flow bottleneck ranking identifies the top constrained component.
- Deployment before/after windows detect API latency, error-rate, and Kafka lag regressions.
- Deployment events are matched to related runtime evidence before broad correlation is emitted.
- All-domain flow inputs produce a deployment-regression root-cause narrative.
- Diagnostic JSON includes Module 3 playbooks.
- Backstage catalog metadata imports owner, criticality, business impact, and blast radius.
- Organization service-matching patterns map runtime flow names to canonical topology services.

## Non-Goals

Module 3 is not yet:

- full live service graph discovery
- log ingestion
- distributed tracing storage
- automatic topology mutation
- auto-remediation
- AI-only root-cause reasoning

## Next Engineering Priorities

1. Match deployment events to affected services/components by name and namespace.
2. Add live topology discovery adapters after snapshot workflows are stable.
3. Add per-organization tuning thresholds for deployment windows.
4. Add regex service matching overrides only if glob-style patterns prove insufficient.
5. Add source-line or telemetry-sample drilldowns when collectors provide stable offsets.
