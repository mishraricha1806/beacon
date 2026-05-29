
# Beacon Architecture

Beacon is a production-readiness and operational intelligence platform.

Its purpose is not only to detect bad configuration, but to explain whether infrastructure is production ready, why systems become operationally risky, and what engineers should do next.

---

## Core Product Direction

Beacon has two major intelligence modes:

1. Production Readiness Intelligence  
   Answers: Is this system safe for production?

2. Runtime Operational Intelligence  
   Answers: Why is this system degrading?

The architecture must support both without becoming chaotic.

---

## Design Principles

Beacon follows these principles:

- Deterministic first, AI second
- Read-only runtime access by default
- Metadata-driven findings
- Normalized resources before rule evaluation
- Small focused rules
- Policy-aware execution
- Evidence-rich reporting
- No heavy telemetry ingestion
- No mutation of production systems

---

## High-Level Architecture

```text
Input Sources
  ├── Terraform
  ├── Terraform plan/state JSON
  ├── Kafka YAML
  ├── Kubernetes YAML
  ├── Helm charts
  ├── CI/CD workflow YAML
  ├── Cloud inventory snapshots
  ├── Service topology snapshots
  ├── Runtime Snapshot YAML
  └── Live Runtime Connectors
      ├── Kafka metadata/config collector
      └── Kubernetes kubectl collector
          ↓
Resource Normalization
          ↓
Rule Registry
          ↓
Evaluator Engine
          ↓
Structured Findings
          ↓
Readiness Engine
          ↓
Reports / JSON / HTML
          ↓
Future: Correlation + AI Reasoning
````

---

## Current Architecture

```text
beacon/
├── cli.py
├── scanner.py
├── reporter.py
├── html_report.py
│
├── rules/
│   ├── models.py
│   ├── static_engine.py
│   ├── kafka_registered_rules.py
│   ├── storage_registered_rules.py
│   ├── iam_registered_rules.py
│   ├── kubernetes_registered_rules.py
│   ├── kubernetes_runtime_registered_rules.py
│   ├── cloud_registered_rules.py
│   ├── cicd_registered_rules.py
│   └── topology_registered_rules.py
│
├── readiness/
│   ├── readiness_reporter.py
│   └── kafka/
│       └── readiness_engine.py
│
├── engine/
│   ├── rule_model.py
│   ├── registry.py
│   ├── evaluator.py
│   ├── resource_normalizer.py
│   ├── policy_engine.py
│   └── graph.py
│
├── runtime_advisor.py
├── kafka_runtime_connector.py
└── kubernetes_runtime_connector.py
```

---

## Target Architecture

```text
beacon/
├── cli/
├── scan/
├── diagnose/
├── readiness/
├── engine/
├── rules/
├── collectors/
├── normalizers/
├── policies/
├── topology/
├── correlations/
├── reporting/
└── ai/
```

This target should be reached gradually, not through a large rewrite.

---

## Core Data Flow

### Static Readiness Flow

```text
Terraform / Terraform JSON / YAML / Helm / CI/CD Manifest / Cloud Inventory / Topology
        ↓
Scanner
        ↓
Resource Normalizer
        ↓
Rule Registry
        ↓
Evaluator Engine
        ↓
Structured Findings
        ↓
Readiness Engine
        ↓
Terminal / JSON / HTML Report
```

Helm charts are scanned by rendering with `helm template --include-crds` when the Helm CLI is available. If Helm is unavailable or the chart does not render, Beacon emits an analysis error rather than silently skipping the chart.

### Direct Server Readiness Flow

```text
Kafka bootstrap server + direct connection options
        ↓
Direct server configuration validation
        ↓
Read-only Kafka metadata collector
        ↓
Kafka topic + broker config normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Runtime health and lag findings
        ↓
Readiness Engine
        ↓
Terminal / JSON / HTML Report
```

Direct server readiness is read-only by contract. Invalid connection settings and connection failures produce `ERROR` findings and force `NOT READY` / `ANALYSIS BLOCKED` rather than pretending the system is healthy.

### Kubernetes Runtime Readiness Flow

```text
kubectl context / namespace / kubeconfig
        ↓
Read-only Kubernetes collector
        ↓
Nodes + pods + deployments snapshot
        ↓
Kubernetes runtime normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Readiness Engine
        ↓
Terminal / JSON / HTML Report
```

The Kubernetes connector only uses read-only `kubectl get` calls. Missing `kubectl` or collection failures produce `ERROR` findings so readiness does not pass on incomplete runtime data.

### Runtime Diagnostic Flow

```text
Kafka / Kubernetes / API / Database / Storage / Flow Snapshot / Prometheus / OpenTelemetry / Future Splunk
        ↓
Runtime Collector
        ↓
Normalized Runtime Signals
        ↓
Runtime Analyzer
        ↓
Operational Findings
        ↓
Decision Engine
        ↓
Report
```

### Flow Intelligence Runtime Flow

```text
API + Kafka + Consumer + Database + Deployment Signals
        ↓
Flow Runtime Snapshot
        ↓
Flow Runtime Normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Cross-System Operational Findings
        ↓
Readiness Engine / Report
```

Flow Intelligence is Beacon's bridge from individual runtime domains into operational causality. The first deterministic model supports snapshot-based reasoning for downstream database bottlenecks, deployment-correlated degradation, cascading latency, and unhealthy flow components.

### API, Database, And Storage Runtime Flow

```text
API / Database / Storage Runtime Snapshot
        ↓
Runtime Resource Normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Operational Findings
        ↓
Readiness Engine / Report
```

These runtime domains are snapshot-first in Module 1. Beacon can detect API latency/errors/timeouts/retry amplification, database latency/connection pool/replication lag/lock/storage issues, and storage capacity/growth/I/O/backup risks before live collectors exist.

### Prometheus Runtime Collection Flow

```text
Prometheus Query Config
        ↓
Read-only Prometheus HTTP API Queries
        ↓
Runtime Snapshot Mapping
        ↓
Runtime Resource Normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Readiness Engine / Report
```

Prometheus support is intentionally config-driven. Beacon does not store metrics; it asks for the exact runtime signals needed by deterministic API, database, storage, Kubernetes, and Flow rules.

### OpenTelemetry Runtime Mapping Flow

```text
OpenTelemetry Span / Metric Export
        ↓
Runtime Signal Derivation
        ↓
Runtime Snapshot Mapping
        ↓
Runtime Resource Normalization
        ↓
Rule Registry + Evaluator Engine
        ↓
Readiness Engine / Report
```

OpenTelemetry support is export-first in this slice. Beacon reads spans and metric samples, derives API latency/error/timeout/retry signals, database latency and capacity signals, storage signals, and Flow signals without becoming a telemetry store.

---

## Finding Contract

Every finding must follow this structure:

```json
{
  "rule_id": "kafka.topic.replication_factor.low",
  "domain": "kafka",
  "category": "resiliency",
  "severity": "CRITICAL",
  "title": "Kafka topic has low replication factor",
  "impact": "Broker failure may make the topic unavailable.",
  "recommendation": "Use replication_factor=3 for production topics.",
  "file": "examples/bad-infra/kafka-topics.yaml",
  "evidence": {
    "topic": "payments",
    "replication_factor": 1,
    "expected_minimum": 3
  },
  "tags": ["availability", "resiliency"]
}
```

This contract is mandatory.

Do not add findings without `rule_id`, `domain`, `category`, and `evidence`.

---

## Rule Architecture

Rules should be small, focused, and resource-driven.

Legacy pattern:

```python
def evaluate_kafka_config(data):
    for topic in data["topics"]:
        ...
```

Module 1 release pattern:

```python
def replication_factor_rule(resource, context):
    if resource.type != "kafka_topic":
        return None

    if resource.attributes["replication_factor"] < 3:
        return [finding(...)]
```

Rules should not know raw YAML, Terraform, or Kubernetes structure.

Rules should evaluate normalized resources.

The static scanner now follows this path for Module 1 release. `beacon.rules.kafka_rules`, `beacon.rules.terraform_rules`, and `beacon.rules.kubernetes_rules` are compatibility shims that delegate into the normalized static engine.

---

## Resource Normalization

Beacon should normalize input-specific data into stable internal resources.

Example:

```json
{
  "type": "kafka_topic",
  "name": "payments",
  "replication_factor": 1,
  "partitions": 2,
  "retention_ms": 3600000,
  "retention_bytes": null,
  "cleanup_policy": null,
  "min_insync_replicas": null
}
```

This enables the same rule engine to work across:

* YAML configs
* Terraform
* Terraform plan/state JSON
* Helm-rendered manifests
* runtime snapshots
* cloud inventory snapshots
* service topology snapshots
* live Kafka metadata
* live Kubernetes metadata
* future API collectors

---

## Rule Registry

The rule registry is responsible for holding all available rules.

Each rule should have:

```python
Rule(
    rule_id="kafka.topic.replication_factor.low",
    domain="kafka",
    category="resiliency",
    severity="CRITICAL",
    title="Kafka replication factor too low",
    evaluator=replication_factor_rule,
    supported_types=["kafka_topic"],
    tags=["availability", "resiliency"],
)
```

The registry enables:

* policy overrides
* rule discovery
* enterprise governance
* documentation generation
* AI-safe reasoning
* correlation later

---

## Evaluator Engine

The evaluator engine executes registered rules against normalized resources.

Responsibilities:

* run only rules matching the resource type
* skip disabled rules
* catch rule execution errors
* produce structured findings
* apply policy overrides later

---

## Policy Engine

The policy engine should allow organizations to override rule behavior.

Example:

```yaml
kafka.topic.replication_factor.low:
  enabled: true
  severity: HIGH
```

Future policy capabilities:

* disable rules
* override severity
* define environment-specific thresholds
* approve temporary exceptions
* add ownership metadata
* support governance workflows

---

## Readiness Engine

The readiness engine converts findings into business-friendly production decisions.

It should answer:

```text
Is this system production ready?
What is the primary risk area?
What is the operational survivability level?
What should be fixed first?
```

Current readiness categories:

* resiliency
* scalability
* storage sustainability
* operational safety
* recovery readiness

Example output:

```text
Production Decision: NOT READY
Operational Survivability: CRITICAL RISK
Primary Risk Area: Storage Sustainability
Recommended Action: Resolve critical findings before rollout.
```

---

## Runtime Safety

Runtime diagnostics must be read-only.

Beacon must not:

* consume business messages
* produce messages
* alter topics
* delete topics
* modify ACLs
* update consumer offsets
* mutate infrastructure

Runtime connectors should use:

* short timeouts
* max topic limits
* max group limits
* internal topic skipping
* metadata, configuration, and offset APIs only
* read-only Kubernetes discovery calls only

---

## Runtime Kafka Direction

Kafka is Beacon’s first deep runtime domain.

Current and planned Kafka intelligence:

* broker metadata analysis
* broker/server configuration analysis
* topic configuration analysis
* replication readiness
* retention and storage risk
* consumer lag diagnostics
* hot partition detection
* production readiness scoring
* future rebalance storm analysis
* future producer throughput correlation
* future deployment correlation

Kafka is the wedge, not the boundary.

Beacon’s long-term identity remains broader production-readiness and operational intelligence.

---

## Future Correlation Engine

The correlation engine will combine findings across domains.

Example:

```text
Kafka lag high
+ consumer replicas low
+ Kubernetes CPU throttling
+ DB latency increased
= likely consumer-side bottleneck
```

This requires:

* structured findings
* normalized resources
* topology graph
* runtime signal model
* rule metadata

---

## Future Graph Model

Beacon should eventually build an infrastructure graph:

```text
service
  ↓
deployment
  ↓
pod
  ↓
consumer group
  ↓
topic
  ↓
broker
  ↓
storage
```

This graph enables:

* blast radius analysis
* dependency reasoning
* root cause correlation
* production survivability analysis

Beacon now has a first deterministic topology input for Module 1: service snapshots can express owners, criticality, replicas, dependencies, and blast-radius signals. This is not yet a full live graph collector, but it gives the readiness engine a stable model for release-grade blast-radius findings.

---

## Release Boundary

Module 1 is release-ready as a deterministic production-readiness module when used for the supported surfaces below:

* Terraform files and Terraform plan/state JSON
* Helm charts that can be rendered with the local Helm CLI
* Kubernetes YAML
* Kubernetes runtime snapshots and live read-only `kubectl` collection
* API, database, and storage runtime snapshots
* Prometheus query configs mapped into runtime snapshots
* OpenTelemetry spans and metric exports mapped into runtime snapshots
* Kafka topic configuration files
* Kafka broker/server configuration files and live read-only broker config collection where the cluster permits it
* Kafka direct server metadata and consumer group lag diagnostics
* CI/CD workflow YAML
* object storage, IAM, and selected AWS cloud inventory risks
* topology/blast-radius snapshots
* flow runtime snapshots for API -> Kafka -> consumer -> database degradation
* readiness score, readiness decision, JSON output, and HTML reports

The remaining broad-platform gaps are real API integrations, not rule-engine cleanup:

* direct AWS/GCP/Azure account collectors
* richer Terraform module and drift interpretation
* full live service dependency graph construction
* live deployment event correlation
* deeper Kubernetes capacity and workload history
* live cross-system flow collectors
* live API, database, and storage collectors
* broader OpenTelemetry collector integrations

---

## What Beacon Must Not Become

Beacon must not become:

* generic observability platform
* log ingestion system
* metrics database
* dashboard-heavy monitoring tool
* random AI DevOps chatbot

Beacon must become:

* production-readiness intelligence engine
* operational reasoning layer
* runtime diagnosis assistant
* survivability assessment platform

---

## Current Module 1 Goal

Module 1 is Production Readiness Intelligence.

Release scope:

* Terraform scan
* Terraform plan/state scan
* Helm chart rendering and scan
* Kafka config scan
* Kafka broker/server config scan
* Kubernetes YAML scan
* Kubernetes runtime scan
* Flow runtime scan
* CI/CD workflow scan
* object storage readiness
* IAM risk detection
* selected cloud inventory readiness
* service topology/blast-radius readiness
* structured findings
* production readiness score
* executive summary
* JSON output
* HTML report
* policy-ready rule metadata

Module 1 is complete only when:

```text
beacon readiness static ./examples/bad-infra
```

and the direct runtime readiness commands produce correct, business-friendly reports with structured evidence and explicit analysis-blocking errors when required tools or connections fail.

---

## Next Engineering Priorities

1. Add cloud account collectors for AWS, GCP, and Azure.
2. Add deployment event ingestion for rollback and blast-radius decisions.
3. Expand topology from snapshots into a discovered service graph.
4. Add Kubernetes capacity and historical degradation signals.
5. Build flow diagnostics across API, Kafka, consumer, and database paths.
6. Improve HTML report drilldowns for evidence, ownership, and remediation priority.

---

## Long-Term Vision

Beacon should help teams answer:

Before production:

```text
Is this system operationally safe?
```

During production:

```text
Why is this system degrading?
```

During incident response:

```text
What should we do first?
```

This is Beacon’s core product direction.
