# Beacon

Production-readiness intelligence for modern infrastructure.

Beacon detects risky infrastructure configurations, operational anti-patterns, and runtime infrastructure risks before they impact production systems.

---

## Why Beacon?

Modern infrastructure failures are rarely caused by a single metric.

Operational issues often emerge from a combination of:

* weak Terraform configurations
* Kafka scaling mistakes
* storage pressure
* replication imbalance
* consumer lag
* infrastructure growth patterns
* unsafe operational defaults

Beacon helps platform engineers understand infrastructure risk before and during production.

---

## Current Capabilities

### Infrastructure Review

Beacon analyzes infrastructure configurations and detects:

* Kafka production-readiness risks
* Terraform infrastructure weaknesses
* Object storage exposure risks
* Kafka storage configuration issues
* IAM permission risks
* Operational anti-patterns

---

### Runtime Kafka Intelligence

Beacon can analyze runtime Kafka signals and recommend whether teams should:

* expand broker disk capacity
* optimize retention and cleanup
* investigate producer behavior
* investigate consumer lag
* review message size growth
* rebalance operational workloads

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

## Example: Runtime Kafka Advisor

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

## Current Support

### Infrastructure Providers

* Terraform
* Kafka configurations
* AWS object storage
* GCP object storage
* Azure storage configurations

### Runtime Intelligence

* Kafka disk pressure analysis
* Consumer lag impact analysis
* Producer throughput growth analysis
* Storage growth reasoning
* Capacity recommendation engine

---

## Philosophy

Beacon is designed to behave like a senior platform architect reviewing infrastructure and operational behavior for production readiness.

The goal is not just detecting configuration issues,
but helping engineers understand WHY infrastructure becomes operationally risky.

---

## Roadmap

### Near-Term

* Real Kafka cluster integration
* Kafka Admin API support
* Prometheus metrics ingestion
* Dynatrace integration
* Datadog integration
* GitHub PR reviews

### Long-Term

* Infrastructure graph intelligence
* Deployment risk analysis
* Runtime operational reasoning
* Kubernetes operational intelligence
* AI-assisted infrastructure diagnostics

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

Run runtime Kafka advisor:

```bash
python3 -m beacon.cli runtime ./examples/runtime/kafka-runtime.yaml
```

## Planned Secure Kafka Runtime Connection

Beacon currently supports runtime analysis using a YAML snapshot.

Future versions will support direct Kafka cluster analysis using:

```bash
python3 -m beacon.cli runtime-kafka \
  --bootstrap-server kafka1.example.com:9093 \
  --security-protocol SSL \
  --ca-cert /secure/path/ca.pem \
  --client-cert /secure/path/client.pem \
  --client-key /secure/path/client.key

## Planned Secure Kafka Runtime Connection

Beacon currently supports runtime analysis using a YAML snapshot.

Future versions will support direct Kafka cluster analysis using:

```bash
python3 -m beacon.cli runtime-kafka \
  --bootstrap-server kafka1.example.com:9093 \
  --security-protocol SSL \
  --ca-cert /secure/path/ca.pem \
  --client-cert /secure/path/client.pem \
  --client-key /secure/path/client.key


Direct Kafka bootstrap-server runtime connection is planned, not yet implemented.