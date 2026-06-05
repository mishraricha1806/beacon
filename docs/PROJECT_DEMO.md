# Beacon Project Demo

This is the end-to-end demo for Beacon as a product, not just a rule scanner.

The demo shows three product moments:

- Before production: Beacon answers whether infrastructure is release-ready.
- During degradation: Beacon explains why Kafka/runtime signals look unhealthy.
- During recovery: Beacon recommends the first operational actions and evidence to collect.

## Run The Demo

```bash
scripts/demo_project.sh
```

The script uses only local example files. It does not connect to a live Kafka
cluster, Kubernetes cluster, cloud account, Prometheus endpoint, or Schema
Registry endpoint.

Generated JSON artifacts are written to:

```text
reports/project-demo/
```

## What The Demo Covers

### 1. Module 1: Production Readiness

Command:

```bash
python3 -m beacon.cli readiness static examples/supported \
  --environment prod \
  --context examples/supported/intelligence/context.yaml \
  --no-open-report
```

Talk track:

Beacon normalizes Terraform, Kubernetes, Kafka, CI/CD, cloud, topology, and
runtime-style example inputs into deterministic findings. The score, decision,
top reasons, and next actions are rule-backed. AI is not required to trust the
result.

Point out:

- readiness score
- production decision
- top reasons
- environment/context-aware interpretation
- HTML report generated at `reports/report.html`

### 2. Module 1: Environment-Aware Readiness

Command:

```bash
python3 -m beacon.cli readiness static examples/bad-infra \
  --environment dev \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report
```

Talk track:

Beacon should not blindly punish every non-production cluster like production.
The context file lets rules and scoring become organization-aware while staying
deterministic.

Point out:

- dev vs prod profile behavior
- reduced false confidence from generic rules
- context as deterministic intelligence, not RAG hallucination

### 3. Module 2: Kafka Runtime Incident Diagnosis

Command:

```bash
python3 -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/quota-throttle-runtime.yaml \
  --no-open-report
```

Talk track:

Beacon is now diagnosing a runtime incident from read-only Kafka signals. The
important output is not a long list of findings; it is the incident diagnosis,
evidence quality, runbook, and first actions.

Point out:

- Incident Diagnosis
- Evidence Quality
- Why Beacon thinks this
- What to do first
- Runbook
- Evidence still needed

### 4. Module 2: Consumer Group Instability

Command:

```bash
python3 -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml \
  --no-html \
  --no-open-report
```

Talk track:

This demonstrates Kafka consumer instability: rebalance/member churn symptoms
are translated into a diagnosis and operational next steps.

Point out:

- consumer group diagnosis
- actionable vs needs-more-evidence quality
- first actions before scaling brokers

### 5. Module 3: Flow Intelligence

Command:

```bash
python3 -m beacon.cli diagnose flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report
```

Talk track:

Beacon correlates API, Kafka, consumer, database, and deployment-style signals
to rank where the bottleneck likely is. This is the bridge from Kafka-first
diagnostics to distributed system reasoning.

Point out:

- flow bottleneck ranking
- downstream database bottleneck hypothesis
- cascading latency explanation
- deployment-triggered degradation support

### 6. End-To-End Bundle

Command:

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

Talk track:

This is the Beacon product shape: multiple infrastructure and runtime signals
go in, one deterministic operational diagnosis comes out.

## UI Demo

Start the local UI:

```bash
python3 -m beacon.ui
```

Open:

```text
http://127.0.0.1:8765
```

Suggested UI path:

1. Select Kafka.
2. Use `Kafka incident demo` and choose `Quota / throttling pressure`.
3. Run the check.
4. Show Incident Diagnosis, Evidence Quality, Runbook, and findings.
5. Switch to `Rebalance storm` and compare the diagnosis.

## Demo Positioning

Use this language:

```text
Beacon is not a dashboard, log store, or generic AI chatbot.
Beacon is a deterministic operational reasoning layer.
It turns infrastructure and runtime signals into readiness decisions,
incident diagnoses, and next operational actions.
```

## Release Confidence

The demo ends by running:

```bash
python3 scripts/module1_release_check.py
python3 scripts/module2_diagnostic_check.py
python3 scripts/module3_flow_check.py
```

For a full local verification:

```bash
python3 scripts/release_check_all.py
```
