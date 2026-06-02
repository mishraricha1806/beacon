# Module 2 Runtime Diagnostics

Module 2 is Beacon's runtime operational diagnostics layer.

It answers:

- why the system is degrading
- which root-cause hypotheses are most likely
- what engineers should investigate first
- what telemetry is still missing before Beacon can be more confident

Module 2 does not replace Module 1 readiness scoring. It uses runtime findings and correlation rules to produce a `diagnostic_summary`.

## Current Diagnostic Contract

`diagnostic_summary` includes:

- `diagnostic_status`
- `executive_summary`
- `primary_hypothesis`
- `root_cause_hypotheses`
- `diagnostic_playbooks`
- `affected_domains`
- `material_findings`
- `first_actions`
- `evidence_summary`
- `telemetry_gaps`
- `scope`

## Example Commands

```bash
python3 scripts/module2_diagnostic_check.py

python3 -m beacon.cli diagnose snapshot examples/supported/runtime/all-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json

python3 -m beacon.cli diagnose flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report

python3 -m beacon.cli diagnose kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report
```

## Current Scope

Supported diagnostic inputs:

- runtime snapshots
- Kafka live/runtime/history signals
- Flow runtime snapshots
- Kubernetes runtime signals
- Prometheus collector config
- OpenTelemetry exports
- Schema Registry config

The first stable Module 2 behavior is deterministic root-cause ranking. For example:

- Flow + database pressure can rank downstream database bottleneck.
- API timeout + retry + flow cascade can rank retry cascade.
- Kafka lag alone does not claim database bottleneck; Beacon reports telemetry gaps.

## Diagnostic Playbooks

Beacon maps runtime findings to product use cases so reports explain what question
the evidence can currently answer.

Current playbooks:

- Module 2: Why is Kafka consumer lag increasing?
- Module 2: Should we scale Kafka or optimize consumers/configuration?
- Module 2: Why is one partition overloaded?
- Module 2: Why are consumers unstable?
- Module 2: Is Kafka itself unhealthy or is the problem downstream?
- Module 2: Can this system replay backlog before retention expires?
- Module 2: Could schema or poison messages break consumers?
- Module 2: Are clients failing because of auth, ACLs, quotas, or throttling?
- Module 2: Is Kubernetes workload instability driving runtime degradation?
- Module 2: Is platform capacity pressure causing degradation?
- Module 3: Where is the bottleneck across the flow?
- Module 3: Did deployment trigger degradation?
- Module 3: Why is latency cascading across systems?

Each playbook includes:

- confidence
- matched rule IDs
- matched root-cause correlation IDs
- evidence still needed

This keeps Module 2 deterministic. Beacon should not claim a downstream database
bottleneck from Kafka lag alone; it should require flow/database evidence or state
the missing telemetry explicitly.

## Release Gate

Run:

```bash
python3 scripts/module2_diagnostic_check.py
```

The gate verifies:

- Kafka lag alone does not create a downstream database bottleneck hypothesis.
- Flow plus database evidence ranks downstream database bottleneck.
- Retry cascade outranks generic storage pressure when timeout/retry evidence is present.
- Operational playbooks are emitted for Kafka health, replay, schema, auth/quota,
  Kubernetes instability, and platform capacity pressure.
- `diagnose` JSON output is valid and includes `diagnostic_summary`.
- HTML output renders Runtime Diagnosis and matched diagnostic playbooks.
