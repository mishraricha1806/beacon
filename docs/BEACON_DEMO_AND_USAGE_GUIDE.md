# Beacon Demo and Usage Guide

Beacon is a deterministic production-readiness and operational intelligence tool for distributed systems.

Its first product promise is simple:

```text
Run Beacon before production.
Understand whether the system is ready, what can break, and what to fix first.
```

Beacon is read-only. It scans configuration, metadata, snapshots, and exported runtime signals. It does not produce Kafka messages, consume messages, mutate topics, reset offsets, change ACLs, update infrastructure, or modify cluster state.

---

## 1. What Beacon Does

Beacon helps engineering teams answer:

- Is this system production ready?
- What are the highest-risk deployment blockers?
- Can Kafka survive broker failure?
- Are Kubernetes workloads resilient and secure enough?
- Are Terraform/cloud/storage/IAM configs safe?
- Are CI/CD deployment paths controlled?
- Why is runtime degradation happening?
- Is the bottleneck Kafka, consumer, storage, database, API, Kubernetes, or deployment change?
- What should engineers inspect or fix first?

Beacon follows this principle:

```text
Deterministic intelligence first.
AI explanation second.
```

That means Beacon prefers explainable rule-backed findings, evidence, grouped risks, and clear next actions.

---

## 2. Stop the UI

If Beacon UI is running on port `8765`, stop it with `Ctrl+C` in the terminal where it was started.

If you do not know which process is running:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

Then stop that process:

```bash
kill <PID>
```

Verify the port is free:

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
```

No output means the UI is stopped.

---

## 3. Start Beacon UI Locally

From the Beacon repository:

```bash
cd /Users/richamishra/IdeaProjects/beacon
/usr/bin/python3 -m beacon.cli ui --host 127.0.0.1 --port 8765 --no-port-fallback
```

Open:

```text
http://127.0.0.1:8765/
```

If port `8765` is already busy, either stop the old process or use another port:

```bash
/usr/bin/python3 -m beacon.cli ui --host 127.0.0.1 --port 8766
```

Then open:

```text
http://127.0.0.1:8766/
```

---

## 4. UI Scan Instructions

### Static Readiness Scan

Use this for Terraform, Kubernetes YAML, Kafka config, CI/CD, cloud inventory, IAM, storage, and topology files.

Steps:

1. Start the UI.
2. Open `http://127.0.0.1:8765/`.
3. Select domain: `Static readiness` or `All domains`.
4. Choose environment profile:
   - `Dev`
   - `Test`
   - `Staging`
   - `Prod`
5. Upload a static config file under `Static Readiness`.
6. Click the scan/analyze button.
7. Review:
   - Score
   - Decision
   - Critical/High count
   - Top reasons
   - Next actions
   - Root-cause hypotheses
   - Full findings list

### Kafka Live Read-Only Scan

Use this when an engineer wants to connect directly to a Kafka cluster.

Steps:

1. Select domain: `Kafka`.
2. Choose `Direct` mode.
3. Enter bootstrap servers.
   - Comma-separated:

     ```text
     broker-1:9093,broker-2:9093,broker-3:9093
     ```

   - Or one per line.
4. Select security protocol:
   - `PLAINTEXT`
   - `SSL`
   - `SASL_SSL`
5. Upload certificates if needed:
   - CA certificate
   - Client certificate
   - Client key
6. Optional filters:
   - Topic
   - Consumer group
   - Max topics
   - Max groups
7. Optional timeout:
   - `Kafka request timeout ms`
   - Default: `15000`
   - Increase for slow enterprise clusters.
8. Run the scan.

Beacon only uses read-only Kafka AdminClient calls.

### Generic Kafka Access YAML

Use this when an organization has custom auth patterns, such as:

- cluster-level token access
- topic-level client certs
- mTLS
- SASL
- mixed token + cert models

Steps:

1. Select domain: `Kafka`.
2. Select `Access YAML`.
3. Upload the generic access profile YAML.
4. Run the scan.

### Schema Registry Scan

Use this for compatibility and Schema Registry readiness.

Steps:

1. Select domain: `Schema Registry`.
2. Upload Schema Registry config YAML.
3. Run the scan.

Beacon checks compatibility posture and query health in read-only mode.

### Runtime Snapshot Scan

Use this for offline runtime diagnosis without live access.

Steps:

1. Select domain: `Runtime snapshot` or `All domains`.
2. Upload runtime snapshot YAML/JSON.
3. Run the scan.

Supported runtime signals include:

- Kafka lag
- API latency/error/timeout signals
- database latency/connection pool/lock/replication signals
- storage capacity/growth/backup/I/O signals
- Kubernetes runtime health

### Flow Intelligence Scan

Use this to analyze cross-system bottlenecks.

Steps:

1. Select domain: `Flow intelligence`.
2. Upload a flow runtime snapshot.
3. Run the scan.

Beacon can reason across:

```text
API -> Kafka producer -> Kafka topic -> Consumer -> Database
```

### Prometheus and OpenTelemetry

Use this when teams can export metrics or traces.

Steps:

1. Select domain: `Prometheus and OpenTelemetry` or `All domains`.
2. Upload Prometheus config or OpenTelemetry export.
3. Run the scan.

### Kubernetes Live Scan

Use this only when local kubeconfig access is available.

Steps:

1. Select domain: `Kubernetes`.
2. Enable live Kubernetes input if available.
3. Provide namespace/context/kubeconfig if needed.
4. Run the scan.

Beacon reads cluster state; it does not mutate Kubernetes resources.

---

## 5. CLI Quick Start

From the repository:

```bash
cd /Users/richamishra/IdeaProjects/beacon
```

Show help:

```bash
/usr/bin/python3 -m beacon.cli --help
```

Run project-local readiness using `beacon.yaml`:

```bash
/usr/bin/python3 -m beacon.cli readiness
```

Run with JSON output:

```bash
/usr/bin/python3 -m beacon.cli readiness --output json
```

Run doctor:

```bash
/usr/bin/python3 -m beacon.cli doctor
```

Run configured tasks:

```bash
/usr/bin/python3 -m beacon.cli run dev-check
/usr/bin/python3 -m beacon.cli run prod-check
/usr/bin/python3 -m beacon.cli run flow-demo
/usr/bin/python3 -m beacon.cli run kafka-incident-demo
```

---

## 6. CLI Use Cases and Commands

### Use Case 1: Static Production Readiness

Question:

```text
Is this infrastructure safe to deploy?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness static examples/bad-infra --no-html --no-open-report
```

Expected output:

- Production readiness score
- READY / NOT READY decision
- grouped risks
- critical/high findings
- next best actions

### Use Case 2: Full Supported Example Scan

Question:

```text
Can Beacon scan a broad supported example bundle?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness static examples/supported --no-open-report
```

### Use Case 3: All-Domain Readiness

Question:

```text
What is the readiness posture across static config, runtime snapshots, traces, Schema Registry, and deployment events?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report
```

### Use Case 4: Context-Aware Non-Production Interpretation

Question:

```text
Should dev/test findings be interpreted differently from prod?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness static examples/bad-infra \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report
```

Beacon can downgrade or reinterpret findings based on deterministic organization context.

### Use Case 5: Kafka Live Read-Only Diagnostics

Question:

```text
Can this Kafka cluster survive broker failure, lag growth, and storage pressure?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness kafka \
  --bootstrap-server "broker-1:9093,broker-2:9093,broker-3:9093" \
  --security-protocol SSL \
  --ca-cert ./ca.pem \
  --client-cert ./client.pem \
  --client-key ./client.key \
  --max-topics 50 \
  --max-groups 20 \
  --request-timeout-ms 15000 \
  --no-html \
  --no-open-report
```

For runtime incident diagnosis:

```bash
/usr/bin/python3 -m beacon.cli diagnose kafka \
  --bootstrap-server "broker-1:9093,broker-2:9093,broker-3:9093" \
  --security-protocol SSL \
  --ca-cert ./ca.pem \
  --client-cert ./client.pem \
  --client-key ./client.key \
  --topic orders \
  --consumer-group checkout-consumer \
  --request-timeout-ms 15000 \
  --no-html \
  --no-open-report
```

### Use Case 6: Kafka ACL Readiness

Question:

```text
Are Kafka ACLs too broad or unsafe?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness kafka-acls examples/supported/kafka/acls.yaml \
  --no-html \
  --no-open-report
```

### Use Case 7: Kafka History and Churn

Question:

```text
Are consumer groups unstable over time?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report
```

### Use Case 8: Runtime Snapshot Readiness

Question:

```text
What runtime risks are visible from an offline snapshot?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness snapshot examples/supported/runtime/all-runtime.yaml \
  --no-html \
  --no-open-report
```

### Use Case 9: Flow Intelligence

Question:

```text
Where is the bottleneck across API, Kafka, consumer, and database?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report
```

### Use Case 10: Deployment Correlation

Question:

```text
Did a deployment trigger degradation?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli diagnose all \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --no-html \
  --no-open-report
```

### Use Case 11: OpenTelemetry Runtime Readiness

Question:

```text
Do traces/spans show API, database, storage, or flow degradation?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --no-html \
  --no-open-report
```

### Use Case 12: Schema Registry Readiness

Question:

```text
Is Schema Registry compatibility safe for production?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli readiness schema-registry examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report
```

### Use Case 13: Rule Metadata Catalog

Question:

```text
Which deterministic rules does Beacon know about?
```

Command:

```bash
/usr/bin/python3 -m beacon.cli rules list
```

JSON:

```bash
/usr/bin/python3 -m beacon.cli rules list --output json
```

---

## 7. Docker Demo Without Sharing Source Code

This is the best path when you do not want to distribute a macOS `.pkg` or share source code.

Build local demo image:

```bash
docker build -t beacon-demo:local .
```

Run UI:

```bash
docker run --rm -p 8765:8765 beacon-demo:local ui --host 0.0.0.0 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

Run demo static scan:

```bash
docker run --rm beacon-demo:local readiness static /workspace/examples/bad-infra --no-html --no-open-report
```

Scan a user's local project:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  beacon-demo:local readiness static /workspace/project --no-html --no-open-report
```

Shortcut script from this repo:

```bash
./scripts/demo_container.sh ui
./scripts/demo_container.sh readiness
./scripts/demo_container.sh demo
```

Why Docker is the best fast-sharing path:

- no Apple Developer account
- no macOS notarization
- works on macOS, Linux, and Windows with Docker Desktop
- source code does not need to be distributed in the final runtime image
- users can run locally
- easy to demo UI and CLI

---

## 8. Covered Product Use Cases

### Module 1: Production Readiness

Covered:

- Kafka topic replication factor risk
- Kafka min ISR readiness
- Kafka retention and replay risk
- Kafka message size risk
- Kafka partition-count risk with environment-aware severity
- Kafka owner metadata governance
- Kafka compaction and storage multiplier checks
- Kubernetes probes
- Kubernetes replicas
- Kubernetes image tag safety
- Kubernetes topology spread
- Kubernetes PodDisruptionBudget
- Kubernetes NetworkPolicy
- Kubernetes host namespace risk
- Kubernetes container hardening:
  - run as non-root
  - privilege escalation
  - read-only root filesystem
  - seccomp profile
- Terraform static scanning
- Helm-rendered manifest scanning when Helm is available
- object storage public access
- object storage encryption
- object storage lifecycle/retention risk
- IAM wildcard permissions
- IAM admin/owner excessive permissions
- AWS/GCP/Azure IAM patterns
- cloud autoscaling headroom
- cloud quota headroom
- RDS Multi-AZ
- RDS private subnet placement
- VPC endpoint private DNS
- single-region production concentration
- GitHub Actions broad permissions
- unpinned third-party GitHub Actions
- missing deployment timeout
- missing deployment concurrency guard
- topology and blast-radius readiness
- readiness score
- release decision
- grouped risks
- top reasons
- next best actions
- HTML/JSON reports
- module release check

### Module 2: Runtime Operational Diagnostics

Covered:

- Kafka live read-only connection
- multiple Kafka bootstrap servers
- SSL/mTLS certificate support
- generic access profile YAML
- topic filtering
- consumer group filtering
- max topic/group limits
- configurable Kafka timeout
- Kafka consumer lag
- missing committed offsets
- broker count
- topic count
- partition count
- replication/ISR signals
- large message settings
- retention/storage pressure
- Schema Registry read-only query mode
- Schema Registry compatibility mode
- Kafka ACL export diagnostics
- Kafka history diagnostics
- consumer group churn sampling
- runtime snapshot diagnostics
- API latency/error/timeout/retry amplification
- database latency/connection pool/lock/replication symptoms
- storage capacity/growth/backup/I/O pressure
- Kubernetes runtime health from snapshots/live collector
- deterministic root-cause hypotheses
- incident scenario demos

### Module 3: Flow Intelligence

Covered:

- API to Kafka to consumer to database flow reasoning
- downstream database bottleneck hypothesis
- storage/capacity pressure hypothesis
- retry cascade hypothesis
- deployment regression hypothesis
- API degradation correlated with deployment
- Kafka lag correlated with deployment history
- flow runtime cascading latency
- flow bottleneck ranking
- deployment event correlation
- cross-system runtime evidence summaries

### Cross-Domain Readiness Correlations

Covered:

- internet-exposed database path
- public unencrypted object storage exposure
- uncontrolled production deploy path
- Kubernetes compounding single-point-of-failure risk
- cloud quota/autoscaling capacity plan mismatch

---

## 9. What to Tell a New User

Short pitch:

```text
Beacon checks whether distributed infrastructure is production-ready before release.
It scans config, runtime snapshots, Kafka metadata, Kubernetes manifests, cloud/IAM/storage posture, and deployment signals.
It produces a readiness score, top risks, grouped root causes, and next actions.
```

Demo pitch:

```text
Give Beacon your infrastructure config or read-only runtime metadata.
Beacon tells you whether the system is ready, what can fail, and what to fix first.
```

Safety pitch:

```text
Beacon is read-only. It does not mutate Kafka, Kubernetes, cloud, databases, or infrastructure.
```

---

## 10. Recommended Demo Flow

For a first-time audience:

1. Start with UI:

   ```bash
   /usr/bin/python3 -m beacon.cli ui --host 127.0.0.1 --port 8765
   ```

2. Open:

   ```text
   http://127.0.0.1:8765/
   ```

3. Upload a bad static config or use CLI demo:

   ```bash
   /usr/bin/python3 -m beacon.cli readiness static examples/bad-infra --no-html --no-open-report
   ```

4. Explain:
   - decision
   - score
   - critical/high risks
   - grouped root cause
   - remediation

5. Show Docker version:

   ```bash
   docker run --rm -p 8765:8765 beacon-demo:local ui --host 0.0.0.0 --port 8765
   ```

6. Close with:

   ```text
   Beacon is a production-readiness gate first, then runtime intelligence second.
   ```

