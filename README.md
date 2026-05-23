# Beacon

Production-readiness intelligence for modern infrastructure.

Beacon detects risky infrastructure configurations, operational anti-patterns, and runtime infrastructure risks before they impact production systems.

Beacon combines infrastructure analysis with runtime operational diagnostics to help engineers understand WHY systems become unstable — not just WHAT metric changed.

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
* Terraform infrastructure weaknesses
* object storage exposure risks
* Kafka storage configuration issues
* IAM permission risks
* operational anti-patterns

---

### Runtime Kafka Intelligence

Beacon can connect directly to Kafka in:

# read-only diagnostic mode

and analyze:

* broker metadata
* topic configuration
* replication factor
* retention settings
* partition topology
* consumer group lag
* hot partition symptoms
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

Beacon only uses metadata and offset inspection APIs for diagnostics.

---

## Current Support

### Infrastructure Providers

* Terraform
* Kafka configurations
* AWS object storage
* GCP object storage
* Azure storage configurations

### Runtime Intelligence

* Kafka consumer lag diagnostics
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
├── flow          (planned)
└── kubernetes    (planned)
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
* deployment correlation
* flow diagnostics
* Prometheus metrics ingestion
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
