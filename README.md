# Beacon

Production-readiness intelligence for distributed systems.

Beacon helps engineering teams answer one practical question before release:

```text
Is this system production ready?
```

It scans infrastructure configuration, runtime snapshots, and operational
signals, then produces a deterministic readiness decision, ranked risks,
root-cause hypotheses, and next actions.

Beacon is not a dashboard, log store, or generic observability platform. Its
core product principle is:

```text
Deterministic intelligence first. AI explanation second.
```

## What Beacon Does

Beacon currently focuses on three release modules:

| Module | Status | Purpose |
| --- | --- | --- |
| Module 1 | Stable/RC | Production readiness scan before release |
| Module 2 | Active | Kafka-first runtime diagnostics |
| Module 3 | Active | Flow intelligence across API, Kafka, consumers, databases, storage, Kubernetes, and deployments |

Beacon can evaluate:

- Kafka topics, brokers, producers, consumers, ACL exports, Schema Registry, and runtime history
- Kubernetes manifests and runtime snapshots
- Terraform HCL, plan JSON, and state JSON
- Helm charts through rendered manifests
- Cloud inventory, object storage, IAM, and CI/CD workflow risk
- API, database, storage, and platform runtime snapshots
- Prometheus collector configs and OpenTelemetry exports
- Cross-system flow degradation and deployment-triggered regression signals

## Fastest Way To Try Beacon

The recommended distribution path is Docker. You do not need Python, source
code, or a macOS installer.

Pull the image:

```bash
docker pull ghcr.io/mishraricha1806/beacon:latest
```

Run the UI:

```bash
docker run --rm -p 8765:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

Use `0.0.0.0` only in the Docker command. In the browser, use
`127.0.0.1` or `localhost`.

If port `8765` is busy:

```bash
docker run --rm -p 8777:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
```

Then open:

```text
http://127.0.0.1:8777/
```

## How Docker Examples Work

The published Beacon image contains the Beacon binary, not this source tree.
To test examples, run commands from a folder that contains an `examples/`
directory and mount that folder into the container:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest --help
```

All example commands below assume your current directory contains:

```text
examples/
```

## Use Case 1: Bad Infra Readiness Gate

Question:

```text
Would this infrastructure be unsafe if released to production?
```

What Beacon checks:

- Kafka replication factor and partition safety
- Kafka retention and message-size risk
- Terraform/storage/IAM production-readiness issues
- Grouped root-cause risks and next actions

### UI Test

1. Start the UI:

   ```bash
   docker run --rm -p 8765:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
   ```

2. Open:

   ```text
   http://127.0.0.1:8765/
   ```

3. Choose the static/readiness input.
4. Upload files from:

   ```text
   examples/bad-infra/
   ```

5. Run the scan and review the readiness score, top reasons, grouped risks,
   and next actions.

### CLI Test

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/bad-infra \
  --environment prod \
  --no-html \
  --no-open-report
```

JSON output:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/bad-infra \
  --environment prod \
  --output json \
  --no-html \
  --no-open-report
```

Expected type of result:

```text
Decision: NOT READY
Top risks: replication, storage/message size, missing owner/governance context
```

## Use Case 2: Black Friday Readiness

Question:

```text
Can this payment/event pipeline survive a peak-traffic launch?
```

What Beacon checks:

- Kafka broker failure survivability
- payment-topic replication and ISR posture
- producer durability and idempotence
- consumer concurrency and retry/DLQ safety
- runtime pressure across API, Kafka, consumer, database, and storage
- whether the likely bottleneck is Kafka, consumers, storage, or downstream DB/API

### UI Test

1. Start the UI:

   ```bash
   docker run --rm -p 8765:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
   ```

2. Open:

   ```text
   http://127.0.0.1:8765/
   ```

3. Upload static input:

   ```text
   examples/demo-black-friday/kafka-config.yaml
   ```

4. Upload runtime snapshot:

   ```text
   examples/demo-black-friday/runtime-snapshot.yaml
   ```

5. Run the report and review the top risks and root-cause hypotheses.

### CLI Static Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/demo-black-friday \
  --environment prod \
  --no-html \
  --no-open-report
```

### Runtime Snapshot Diagnosis

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose snapshot \
  /workspace/project/examples/demo-black-friday/runtime-snapshot.yaml \
  --no-html \
  --no-open-report
```

### Combined Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness all \
  --static-path /workspace/project/examples/demo-black-friday \
  --snapshot /workspace/project/examples/demo-black-friday/runtime-snapshot.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

Expected type of result:

```text
Decision: NOT READY or CONDITIONAL depending on risk profile
Top risks: replication, producer durability, retention/storage growth, DB/API pressure
```

## Use Case 3: Kafka Runtime Diagnostics

Question:

```text
Why is Kafka or a consumer flow degrading right now?
```

Beacon can work with offline runtime snapshots or direct read-only Kafka
connections.

### UI Test With Snapshot

1. Start the UI:

   ```bash
   docker run --rm -p 8765:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
   ```

2. Open:

   ```text
   http://127.0.0.1:8765/
   ```

3. Upload one of:

   ```text
   examples/runtime/kafka-runtime.yaml
   examples/supported/kafka/runtime-v2.yaml
   examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml
   examples/supported/kafka/scenarios/quota-throttle-runtime.yaml
   examples/supported/kafka/scenarios/schema-poison-runtime.yaml
   ```

4. Run diagnostics and review likely cause, evidence, and first actions.

### CLI Kafka Runtime Snapshot

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose kafka-runtime \
  /workspace/project/examples/runtime/kafka-runtime.yaml \
  --no-html \
  --no-open-report
```

### CLI Platform Runtime Snapshot

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose snapshot \
  /workspace/project/examples/supported/runtime/platform-runtime.yaml \
  --no-html \
  --no-open-report
```

### CLI Flow Runtime Diagnosis

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose flow \
  /workspace/project/examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report
```

### Direct Live Kafka Read-Only Diagnosis

Plaintext local Kafka:

```bash
docker run --rm \
  ghcr.io/mishraricha1806/beacon:latest diagnose kafka \
  --bootstrap-server host.docker.internal:9092 \
  --security-protocol PLAINTEXT \
  --max-topics 50 \
  --max-groups 20 \
  --request-timeout-ms 30000 \
  --no-html \
  --no-open-report
```

SSL/mTLS Kafka with mounted certificates:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose kafka \
  --bootstrap-server "broker1:9093,broker2:9093,broker3:9093" \
  --security-protocol SSL \
  --ca-cert /workspace/project/certs/ca.pem \
  --client-cert /workspace/project/certs/client.pem \
  --client-key /workspace/project/certs/client.key \
  --topic payments \
  --consumer-group payment-processor \
  --max-topics 50 \
  --max-groups 20 \
  --request-timeout-ms 30000 \
  --no-html \
  --no-open-report
```

Beacon runtime diagnostics are read-only. Beacon does not produce messages,
consume messages, mutate topics, delete topics, change ACLs, or update offsets.

## Use Case 4: Supported All-Domain Readiness

Question:

```text
Can Beacon combine multiple infrastructure and runtime domains into one release decision?
```

This example covers Kafka, Kubernetes, Terraform, Helm, cloud inventory, CI/CD,
topology, runtime snapshots, OpenTelemetry, Prometheus, Schema Registry, and
flow intelligence.

Some collector-style example configs use placeholder endpoints such as
`schema-registry.local` or `localhost:9090`. If those services are not running,
Beacon will return explicit analysis-blocked findings. That is expected: it
shows how Beacon handles unreachable read-only collectors in a release gate.

### UI Test

1. Start the UI:

   ```bash
   docker run --rm -p 8765:8765 ghcr.io/mishraricha1806/beacon:latest ui --host 0.0.0.0 --port 8765
   ```

2. Open:

   ```text
   http://127.0.0.1:8765/
   ```

3. Use files under:

   ```text
   examples/supported/
   ```

4. Run a combined report and review distributed readiness dimensions.

### CLI Static Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/supported \
  --environment prod \
  --no-html \
  --no-open-report
```

### CLI All-Domain Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness all \
  --static-path /workspace/project/examples/supported \
  --snapshot /workspace/project/examples/supported/runtime/all-runtime.yaml \
  --deployment-events /workspace/project/examples/supported/deployments/events.yaml \
  --opentelemetry /workspace/project/examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry /workspace/project/examples/supported/kafka/schema-registry.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### CLI All-Domain Diagnostics

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose all \
  --static-path /workspace/project/examples/supported \
  --snapshot /workspace/project/examples/supported/runtime/all-runtime.yaml \
  --deployment-events /workspace/project/examples/supported/deployments/events.yaml \
  --opentelemetry /workspace/project/examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry /workspace/project/examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report
```

## Use Case 5: Individual Domain Examples

Run each supported domain independently when you want to isolate behavior.

### Kubernetes Manifest Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/supported/kubernetes \
  --environment prod \
  --no-html \
  --no-open-report
```

### Terraform, Plan, And State Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/supported/terraform \
  --environment prod \
  --no-html \
  --no-open-report
```

### Kafka ACL Export Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness kafka-acls \
  /workspace/project/examples/supported/kafka/acls.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### Kafka History / Churn Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness kafka-history \
  /workspace/project/examples/supported/kafka/history.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### Schema Registry Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness schema-registry \
  /workspace/project/examples/supported/kafka/schema-registry.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### Prometheus-Derived Runtime Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness prometheus \
  /workspace/project/examples/supported/prometheus/platform-prometheus.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### OpenTelemetry-Derived Runtime Readiness

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness opentelemetry \
  /workspace/project/examples/supported/opentelemetry/checkout-otel.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

### Flow Intelligence

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose flow \
  /workspace/project/examples/supported/flow/scenarios/downstream-db-bottleneck.yaml \
  --no-html \
  --no-open-report
```

### Deployment-Triggered Degradation

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose flow \
  /workspace/project/examples/supported/flow/scenarios/deployment-triggered-degradation.yaml \
  --no-html \
  --no-open-report
```

### Cascading Latency

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest diagnose flow \
  /workspace/project/examples/supported/flow/scenarios/cascading-latency.yaml \
  --no-html \
  --no-open-report
```

## Project-Local Config

Beacon supports project-local config discovery with:

```text
beacon.yaml
beacon.yml
.beacon.yaml
```

From source or from a mounted project, you can run:

```bash
beacon init
beacon doctor
beacon readiness
beacon run prod-check
```

With Docker:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness \
  --config /workspace/project/beacon.yaml \
  --output terminal
```

## Output Formats

Terminal output:

```bash
--output terminal
```

JSON output:

```bash
--output json
```

Disable browser report generation in automation:

```bash
--no-html --no-open-report
```

## Environment Profiles

Beacon can interpret findings differently by environment:

```bash
--environment dev
--environment test
--environment staging
--environment prod
```

Use `prod` for strict release gates. Use `dev` or `test` when single-broker,
low-replication, or experimental patterns are expected and should be
interpreted with lower severity.

## Safety Contract

Beacon live diagnostics are read-only.

Beacon does not:

- consume business messages
- produce messages
- alter topics
- delete topics
- mutate ACLs
- update consumer offsets
- mutate Kubernetes resources
- mutate infrastructure

Beacon only reads metadata, configuration, runtime snapshots, offsets, and
status signals.

## Public Distribution Model

Recommended setup:

```text
Private source repo:
- implementation
- tests
- build pipeline
- internal examples

Public distribution repo:
- README
- screenshots
- quick-start commands
- release notes
- safe sample inputs
- links to ghcr.io/mishraricha1806/beacon:latest
```

This lets users run Beacon quickly without receiving the source code.

## Deeper Documentation

- [Module 1 Release](docs/MODULE_1_RELEASE.md)
- [Module 2 Runtime Diagnostics](docs/MODULE_2_RUNTIME_DIAGNOSTICS.md)
- [Module 3 Flow Intelligence](docs/MODULE_3_FLOW_INTELLIGENCE.md)
- [Project Demo](docs/PROJECT_DEMO.md)
- [Demo And Usage Guide](docs/BEACON_DEMO_AND_USAGE_GUIDE.md)
- [Project Local Config](docs/PROJECT_LOCAL_CONFIG.md)
- [Packaging Release](docs/PACKAGING_RELEASE.md)
- [Public Distribution](docs/PUBLIC_DISTRIBUTION.md)
- [Kafka Release](docs/KAFKA_RELEASE.md)

## Product Philosophy

Observability tools show signals.

Beacon explains production readiness and operational risk:

```text
What is unsafe?
Why does it matter?
What should engineers fix first?
```
