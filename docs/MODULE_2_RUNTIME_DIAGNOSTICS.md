# Module 2 Runtime Diagnostics

Module 2 is Beacon's runtime operational diagnostics release.

## Goal

Diagnose runtime degradation safely using read-only collectors and deterministic
reasoning.

Module 2 should answer:

- Why is the system degrading?
- Is the bottleneck Kafka, consumers, producers, retention/storage, or a downstream dependency?
- What should engineers inspect first?
- What evidence is missing before Beacon can be more confident?

Module 2 does not replace Module 1 readiness. Module 1 answers whether a system
is production-ready before rollout. Module 2 answers why a running system is
degrading.

## Initial Domain

Kafka is the initial deep domain.

Kafka is the right wedge because runtime Kafka failures are painful, complex,
and poorly explained by dashboards alone. Beacon should prove depth here before
expanding into broader runtime intelligence.

## Primary Use Cases

### Why is consumer lag increasing?

Beacon analyzes:

- total lag
- lag by group/topic/partition where available
- lag trend across history snapshots
- hot partition symptoms
- committed offset status
- consumer group state
- rebalance and member churn signals
- producer rate trend
- deployment timing signals
- downstream API/database evidence when provided
- broker health evidence when provided

Beacon should not claim a downstream database bottleneck from Kafka lag alone.
Kafka lag alone produces `lag_requires_more_evidence`.

### Is the bottleneck broker, consumer, producer, retention, or downstream?

Beacon maps findings into diagnostic playbooks:

- Kafka consumer lag
- Kafka scale vs optimize
- partition skew
- consumer instability
- Kafka cluster health
- replay survivability
- schema or poison-message risk
- auth, ACL, quota, or throttling risk
- Kubernetes workload instability
- platform capacity pressure

### Should we scale infrastructure or fix application behavior?

Beacon should distinguish:

- broker capacity pressure
- retention/storage guardrail gaps
- producer payload or throughput growth
- consumer-side processing bottlenecks
- downstream API/database latency
- hot partitions where consumer scaling alone is insufficient
- producer-rate increases across the incident window
- deployment-correlated lag growth

### Are we seeing hot partitions?

Beacon detects hot partition symptoms from lag concentration and recommends
checking producer partition-key strategy before scaling consumers blindly.

### Is storage pressure caused by retention, payload size, or lag?

Beacon analyzes:

- disk usage
- disk growth
- retention guardrails
- message size increase
- producer rate increase
- consumer lag under pressure
- replay/retention-window survivability

## Runtime Safety Contract

Beacon runtime diagnostics are read-only.

Beacon must not:

- consume messages
- produce messages
- alter topics
- delete topics
- mutate ACLs
- update offsets
- mutate infrastructure
- perform auto-remediation

Beacon may inspect:

- metadata
- topic and broker configuration
- consumer group offsets
- consumer group state
- ACL metadata where permitted
- runtime snapshots
- Prometheus/OpenTelemetry-derived metrics
- Schema Registry metadata and compatibility settings
- Kafka JMX metrics exposed through Prometheus
- deployment event timelines provided as YAML or JSON

## CLI Contract

Primary live Kafka command:

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server kafka1:9093 \
  --security-protocol SSL \
  --ca-cert ./ca.pem \
  --client-cert ./client.pem \
  --client-key ./client.key \
  --max-topics 50 \
  --max-groups 20
```

Focused consumer group command:

```bash
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server kafka1:9093 \
  --security-protocol SSL \
  --ca-cert ./ca.pem \
  --client-cert ./client.pem \
  --client-key ./client.key \
  --consumer-group checkout-consumer \
  --max-topics 50 \
  --max-groups 20
```

Organizations with split cluster/topic/group credentials can use access
profiles:

```bash
python3 -m beacon.cli diagnose kafka \
  --access-config examples/supported/kafka/access-profiles.yaml \
  --consumer-group checkout-consumer
```

All-domain diagnosis can correlate deployment events with runtime findings:

```bash
python3 -m beacon.cli diagnose all \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --no-html \
  --no-open-report
```

## Output Contract

`diagnostic_summary` includes:

- `diagnostic_status`
- `executive_summary`
- `primary_hypothesis`
- `root_cause_hypotheses`
- `diagnostic_playbooks`
- `consumer_group_diagnoses`
- `affected_domains`
- `material_findings`
- `first_actions`
- `evidence_summary`
- `telemetry_gaps`
- `scope`

`consumer_group_diagnoses` includes:

- `consumer_group`
- `status`
- `total_lag`
- `partition_count`
- `max_partition_lag`
- `hot_partitions`
- `affected_topics`
- `group_state`
- `member_count`
- `committed_offsets_status`
- `primary_likely_cause`
- `confidence`
- `evidence_used`
- `evidence_missing`
- `first_actions`

## Release Gate

Run:

```bash
python3 scripts/module2_diagnostic_check.py
```

The gate verifies:

- Kafka lag alone does not create a downstream database bottleneck hypothesis.
- Kafka incident scenarios emit the expected findings and playbooks for
  rebalance storms, quota/throttling pressure, schema/poison-message risk, and
  hot partitions.
- Flow plus database evidence ranks downstream database bottleneck.
- Retry cascade outranks generic storage pressure when timeout/retry evidence is present.
- Operational playbooks are emitted for Kafka health, replay, schema, auth/quota,
  Kubernetes instability, and platform capacity pressure.
- Deployment events correlate with runtime degradation and emit the
  deployment-triggered playbook.
- Prometheus Kafka JMX mappings produce broker health, ISR, controller, queue,
  network, throttling, schema, and replay findings.
- `diagnose` JSON output is valid and includes `diagnostic_summary`.
- HTML output renders Runtime Diagnosis, matched diagnostic playbooks, and Kafka
  consumer group diagnosis.

## Non-Goals

Module 2 is not:

- an AI agent
- a RAG explanation system
- a log ingestion platform
- a Grafana replacement
- a Splunk replacement
- a full Kubernetes live intelligence platform
- a multi-tenant SaaS control plane
- an auto-remediation system

Those may become later modules, but Module 2 should stay focused on safe,
deterministic runtime diagnosis.

## Next Engineering Priorities

1. Deepen deployment attribution with before/after windows and service matching.
2. Add richer broker/client attribution for Kafka JMX findings.
3. Improve time-window trend modeling for lag, rebalance churn, disk growth,
   producer rate, and deployment correlation.
4. Improve the web UI around focused Kafka consumer-group diagnosis.
