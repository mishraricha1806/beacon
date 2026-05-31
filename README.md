# Beacon

Production-readiness intelligence for modern infrastructure.

Beacon detects risky infrastructure configurations, operational anti-patterns, and runtime infrastructure risks before they impact production systems.

Beacon combines infrastructure analysis with runtime operational diagnostics to help engineers understand WHY systems become unstable — not just WHAT metric changed.

Module 1's release boundary is documented in [docs/MODULE_1_RELEASE.md](docs/MODULE_1_RELEASE.md).

The release gate is codified in `scripts/module1_release_check.py` and `.github/workflows/module1-release.yml`.

---

## Why Beacon?

Modern infrastructure failures are rarely caused by a single metric.

Operational issues often emerge from a combination of:

* weak Terraform configurations
* Kafka scaling mistakes
* storage pressure
* replication imbalance
* consumer lag
* partition imbalance
* downstream dependency slowness
* infrastructure growth patterns
* unsafe operational defaults

Most tools expose telemetry.

Beacon focuses on:

# operational reasoning.

---

## Current Capabilities

### Infrastructure Review

Beacon analyzes infrastructure configurations and detects:

* Kafka production-readiness risks
* Kafka broker/server configuration risks
* Terraform infrastructure weaknesses
* Terraform plan/state JSON risks
* Helm-rendered Kubernetes manifest risks
* Kubernetes manifest readiness risks
* Kubernetes runtime snapshot risks
* CI/CD deployment workflow risks
* object storage exposure risks
* Kafka storage configuration issues
* IAM permission risks
* cloud inventory snapshot risks
* service topology and blast-radius risks
* operational anti-patterns

---

### Runtime Intelligence

Beacon runtime intelligence is multi-domain. Kafka remains the first deep wedge, Kubernetes is the second live runtime surface, and Flow Intelligence connects the signals across systems.

Beacon can connect directly to Kafka and Kubernetes in:

# read-only diagnostic mode

and analyze:

* broker metadata
* topic configuration
* broker security and ACL safety defaults
* producer durability, idempotence, ordering, and compression settings
* consumer offset commit, replay, rebalance, concurrency, and DLQ settings
* rack/AZ awareness, replica placement, and unclean leader election risk
* replication factor
* retention, compaction, tombstone, and key-cardinality settings
* partition topology
* offline partitions and ISR shrink
* leader imbalance
* controller instability and partition reassignment pressure
* replication fetcher lag and broker request queue saturation
* consumer group lag
* consumer group rebalancing or empty membership
* hot partition symptoms
* broker disk skew
* producer error rate, throttling, and request latency pressure
* Schema Registry availability and incompatible schema-change risk
* backlog replay time and retention-window survivability
* storage growth pressure
* operational bottlenecks

Beacon can generate operational recommendations such as:

* investigate downstream DB/API latency
* review partition key strategy
* optimize retention configuration
* review consumer throughput
* increase partition parallelism
* investigate rebalance instability
* review producer throughput growth

Flow Intelligence can analyze runtime snapshots across:

* API latency and timeout signals
* Kafka consumer lag
* consumer retry pressure
* database latency
* deployment timing
* component health

Beacon uses those signals to explain cross-system degradation, such as a likely downstream database bottleneck, deployment-triggered degradation, or cascading latency across API, Kafka, consumers, and the database.

Beacon readiness reports now include deterministic root-cause hypotheses when multiple runtime findings point to the same operational failure mode. These hypotheses rank likely causes such as retry cascades, downstream database bottlenecks, deployment regressions, storage pressure, or Kubernetes workload instability.

Beacon also supports standalone runtime snapshots for:

* API/service latency, errors, timeouts, retry amplification, and deployment-correlated degradation
* database latency, connection pool pressure, replication lag, lock contention, and storage saturation
* storage/cloud capacity, growth rate, I/O saturation, and backup freshness

Prometheus collector configs can also map Kafka JMX exporter metrics into Beacon's Kafka runtime advisor, including broker disk skew, ISR/offline partition health, controller churn, request queue saturation, throttling, and Schema Registry availability.

---

## Example: Infrastructure Scan

```bash
python3 -m beacon.cli scan ./examples/bad-infra
```

Example output:

```text
Beacon Production Readiness Score: 41/100

CRITICAL:
- Kafka topic 'payments' has replication factor 1
- Object storage public access protection is weak

HIGH:
- Kafka topic 'payments' does not define retention_bytes
- Kafka topic 'orders' has high storage multiplier

Impact:
A broker failure can interrupt production workflows and increase recovery risk.
```

---

## Example: Runtime Snapshot Analysis

```bash
python3 -m beacon.cli runtime ./examples/runtime/kafka-runtime.yaml
```

Example runtime decision:

```text
Decision:
Investigate producer/consumer behavior before only expanding disk.

Reason:
Disk usage crossed 80%, while producer throughput,
message size, and consumer lag increased recently.

Recommendation:
Review producer payload changes, consumer processing latency,
retention settings, and topic growth patterns before scaling storage.
```

---

## Example: Live Kafka Diagnostics

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server localhost:9092
```

For organizations with separate cluster and topic credentials, use a generic
access profile config:

```bash
python3 -m beacon.cli diagnose kafka \
  --access-config examples/supported/kafka/access-profiles.yaml \
  --topic payments
```

Run the local Kafka readiness UI:

```bash
python3 -m beacon.ui
```

Then open `http://127.0.0.1:8765` and enter the bootstrap server, certificates,
or access profile YAML. The UI uses the same read-only Kafka diagnostics engine
as the CLI.

---

## Example: Live Kubernetes Diagnostics

```bash
python3 -m beacon.cli diagnose kubernetes \
  --namespace payments \
  --no-open-report
```

Beacon uses read-only `kubectl get` calls for nodes, pods, and deployments, then evaluates normalized runtime resources through the same deterministic rule engine.

---

## Example: Kubernetes Readiness

```bash
python3 -m beacon.cli readiness kubernetes \
  --namespace payments \
  --output json
```

---

## Example: Flow Diagnostics

```bash
python3 -m beacon.cli diagnose flow ./examples/runtime/checkout-flow.yaml
```

Flow diagnostics answer where degradation is most likely coming from across service paths such as:

```text
API -> Kafka -> Consumer -> Database
```

---

## Example: Platform Runtime Snapshot

```bash
python3 -m beacon.cli diagnose snapshot ./examples/runtime/platform-runtime.yaml
```

Use this for API, database, storage, Kubernetes, and Flow runtime snapshots when there is not yet a live collector attached.

---

## Example: Prometheus Runtime Diagnostics

```bash
python3 -m beacon.cli diagnose prometheus \
  ./examples/supported/prometheus/platform-prometheus.yaml
```

Beacon queries Prometheus through read-only HTTP APIs, maps query results into runtime snapshots, and then applies the same deterministic API, database, storage, and Flow rules.

---

## Example: OpenTelemetry Runtime Diagnostics

```bash
python3 -m beacon.cli diagnose opentelemetry \
  ./examples/supported/opentelemetry/checkout-otel.yaml
```

Beacon reads exported OpenTelemetry spans and metric samples, derives API/database/storage/Flow runtime signals, and evaluates them through deterministic runtime rules.

---

## Example: Schema Registry Diagnostics

```bash
python3 -m beacon.cli diagnose schema-registry \
  ./examples/supported/kafka/schema-registry.yaml
```

Beacon queries Schema Registry through read-only HTTP APIs and checks compatibility posture, expected topic subjects, latest schema availability, and schema type visibility.

---

## Example: All-Domain Readiness

```bash
python3 -m beacon.cli readiness all \
  --static-path ./examples/supported \
  --snapshot ./examples/supported/runtime/all-runtime.yaml \
  --opentelemetry ./examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry ./examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report
```

`readiness all` combines every provided domain input into one production-readiness decision. Static inputs cover Terraform, Helm-rendered Kubernetes, Kubernetes YAML, Kafka config, CI/CD, cloud inventory, and topology. Runtime inputs cover API, database, storage, flow, Kubernetes, Kafka snapshots, Prometheus-derived signals, OpenTelemetry-derived signals, Schema Registry metadata, and optional read-only live Kafka/Kubernetes collection.

---

## Example: All-Domain Diagnostics

```bash
python3 -m beacon.cli diagnose all \
  --snapshot ./examples/supported/runtime/all-runtime.yaml \
  --opentelemetry ./examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry ./examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report
```

`diagnose all` uses the same domain inputs, but reports operational findings for investigation instead of producing a production-readiness decision.

---

## Diagnose Specific Topic

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server localhost:9092 \
  --topic payments
```

---

## Diagnose Specific Consumer Group

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server localhost:9092 \
  --consumer-group payment-consumer
```

---

## JSON Output

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server localhost:9092 \
  --output json
```

---

## Example Runtime Findings

```text
HIGH:
High Kafka consumer lag detected for group 'payment-consumer'

Impact:
Consumer lag exceeded operational threshold and may increase processing delay.

Recommendation:
Check downstream DB/API latency, consumer processing time,
rebalance frequency, retry loops, and recent deployments.
```

---

## HTML Report Generation

Beacon automatically generates browser-based HTML reports for:

* infrastructure findings
* operational risk summaries
* runtime diagnostics
* production-readiness scoring

Reports are generated under:

```text
reports/report.html
```

---

## Runtime Safety

Beacon runtime diagnostics are:

# read-only by design

Beacon does NOT:

* consume business messages
* produce messages
* alter topics
* delete topics
* modify ACLs
* update consumer offsets
* mutate infrastructure

Beacon only uses metadata, status, snapshot, and offset inspection signals for diagnostics.

---

## Current Support

### Infrastructure Providers

* Terraform
* Terraform plan/state JSON
* Helm charts through rendered Kubernetes manifests
* Kafka configurations
* Kafka broker/server configurations
* Kubernetes YAML
* Kubernetes runtime snapshots
* GitHub Actions workflow YAML
* AWS object storage
* AWS security groups, RDS, and EC2 inventory snapshots
* GCP object storage
* Azure storage configurations
* cloud inventory snapshots
* service topology snapshots

### Runtime Intelligence

* Kafka consumer lag diagnostics
* Kafka direct server metadata diagnostics
* Kafka broker configuration diagnostics
* Kubernetes node, pod, and deployment diagnostics
* flow runtime snapshot diagnostics
* API/service runtime snapshot diagnostics
* database runtime snapshot diagnostics
* storage/cloud runtime snapshot diagnostics
* Prometheus runtime signal collection
* OpenTelemetry span and metric export analysis
* ranked root-cause hypotheses across runtime findings
* downstream database bottleneck detection
* deployment-correlated degradation detection
* cascading latency detection
* hot partition detection
* partition parallelism analysis
* Kafka storage pressure analysis
* producer throughput growth analysis
* retention configuration analysis
* operational recommendation engine

---

## Diagnose Domains

```text
diagnose/
├── kafka
├── kubernetes
├── flow
├── snapshot
├── prometheus
└── opentelemetry
```

---

## Performance Philosophy

Beacon is designed to be:

* lightweight
* low-latency
* operationally safe
* deterministic-first
* metadata-driven

Beacon intentionally avoids:

* full telemetry ingestion
* heavy broker load
* consuming Kafka traffic
* excessive runtime overhead
* observability platform complexity

---

## Philosophy

Beacon is designed to behave like a senior platform architect reviewing infrastructure and operational behavior for production readiness.

The goal is not just detecting configuration issues,
but helping engineers understand:

* WHY infrastructure becomes operationally risky
* WHY consumer lag increases
* WHY runtime degradation happens
* WHAT operational decision engineers should take next

---

## Roadmap

### Near-Term

* lag trend analysis
* rebalance storm diagnostics
* producer spike analysis
* deeper deployment correlation
* live flow collectors
* broader OpenTelemetry support
* direct cloud provider runtime collectors
* Prometheus metrics ingestion
* richer correlation explanations and remediation playbooks
* Grafana integration
* summarized Splunk log correlation
* GitHub PR reviews

---

### Long-Term

* distributed operational intelligence
* deployment risk analysis
* runtime operational reasoning
* Kubernetes operational intelligence
* AI-assisted root-cause reasoning
* operational pattern memory
* distributed flow correlation engine

---

## Run Locally

Clone repository:

```bash
git clone https://github.com/<your-username>/beacon.git

cd beacon
```

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Run infrastructure review:

```bash
python3 -m beacon.cli scan ./examples/bad-infra
```

Run Kafka runtime diagnostics:

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server localhost:9092
```

---

## Beacon Philosophy

Observability tools show signals.

Beacon focuses on:

# operational causality and runtime reasoning.
