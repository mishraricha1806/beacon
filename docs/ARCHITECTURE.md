
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
  ├── Kafka YAML
  ├── Kubernetes YAML
  ├── Runtime Snapshot YAML
  └── Live Runtime Connectors
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
│   └── kubernetes_registered_rules.py
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
└── kafka_runtime_connector.py
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
Terraform / YAML / Kubernetes Manifest
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

### Direct Server Readiness Flow

```text
Kafka bootstrap server + direct connection options
        ↓
Direct server configuration validation
        ↓
Read-only Kafka metadata collector
        ↓
Kafka topic config normalization
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

### Runtime Diagnostic Flow

```text
Kafka / Snapshot / Future Prometheus / Future Splunk
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
* live Kafka metadata
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
* metadata and offset APIs only

---

## Runtime Kafka Direction

Kafka is Beacon’s first deep runtime domain.

Current and planned Kafka intelligence:

* broker metadata analysis
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

---

## Migration Strategy

Do not rewrite everything at once.

Use controlled migration:

1. Keep current evaluators working.
2. Introduce normalized resource model.
3. Migrate one rule to registry.
4. Validate tests.
5. Migrate remaining rules domain by domain.
6. Remove old evaluator only after parity is proven.

Correct migration order:

```text
Kafka topic rules
→ Object storage rules
→ IAM rules
→ Kubernetes rules
→ Runtime snapshot rules
→ Live runtime rules
```

During migration, correctness is more important than architecture purity.

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

Module 1 is Static Production Readiness.

Final scope:

* Terraform scan
* Kafka config scan
* Kubernetes YAML scan
* object storage readiness
* IAM risk detection
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

produces a correct, business-friendly production readiness report with structured evidence.

---

## Next Engineering Priorities

1. Stabilize rule registry and evaluator framework.
2. Migrate Kafka topic rules to registry.
3. Add tests for registry-driven execution.
4. Keep old evaluator path until rule parity is confirmed.
5. Migrate object storage rules.
6. Update readiness engine to rely only on structured metadata.
7. Improve HTML report with evidence and category drilldown.

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

````

Then commit:

```bash
git add docs/ARCHITECTURE.md
git commit -m "Add Beacon architecture plan"
git push
````
