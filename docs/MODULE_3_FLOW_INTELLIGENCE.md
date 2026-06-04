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
- OpenTelemetry-derived flow signals
- Prometheus-derived runtime signals

Current flow playbooks:

- `module3.flow.bottleneck`
- `module3.flow.deployment_triggered`
- `module3.flow.cascading_latency`

Current diagnostic output:

- `flow_bottleneck_rankings`
- `deployment_window_analyses`

Each flow ranking includes:

- `flow`
- `top_bottleneck`
- `top_confidence`
- ranked components with component type, confidence, status, reason, and matched evidence

Each deployment window analysis includes:

- service
- version
- deployment timestamp
- before/after metrics
- delta and ratio
- severity and matched rule

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
- All-domain flow inputs produce a deployment-regression root-cause narrative.
- Diagnostic JSON includes Module 3 playbooks.

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
2. Connect OpenTelemetry spans to flow components more directly.
3. Add a visual flow path panel for API to Kafka to consumer to database.
4. Add richer evidence-used and evidence-missing panels for each ranked component.
5. Add time-window severity tuning per environment and service tier.
