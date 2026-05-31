# Beacon Module 1 Release Boundary

Module 1 is Beacon's production-readiness intelligence release. It is scoped to deterministic infrastructure and runtime-readiness analysis, with AI-style explanation kept downstream of rule-backed findings.

## Release Scope

Module 1 is ready to release when these surfaces are supported by examples, deterministic rules, and stable readiness output:

- Terraform HCL plus Terraform plan/state JSON
- Helm chart rendering into Kubernetes manifests
- Kubernetes YAML, runtime snapshots, and read-only live cluster collection
- Kafka topic, broker/server configuration, and read-only live metadata/lag collection
- Kafka producer and consumer client configuration risk checks
- Kafka deterministic checks for broker security defaults, rack/AZ safety, schema compatibility, ownership, controller health, reassignment pressure, replication lag, throttling, and request queue saturation
- CI/CD deployment workflow manifests
- Cloud inventory snapshots
- Service topology and blast-radius snapshots
- Runtime snapshots for API, database, storage, flow, Kubernetes, and Kafka signals
- Prometheus collector configs that map metrics into runtime snapshots, including Kafka JMX exporter signals
- OpenTelemetry span/metric exports that map into runtime snapshots
- Deterministic root-cause hypotheses derived from correlated findings

## Non-Goals

Module 1 should not claim to be:

- A telemetry storage engine
- A dashboard-heavy observability platform
- A log ingestion platform
- An AI chatbot for DevOps
- A full cloud account inventory collector
- A full live service graph discovery engine
- A mutation or remediation executor

Those are intentionally outside the first release. Beacon should remain a production-readiness and operational reasoning engine.

## Release Checklist

- Supported examples exist under `examples/supported/` for every release surface.
- Readiness tests cover static examples, runtime snapshots, Prometheus, and OpenTelemetry paths.
- Every registered release rule has metadata.
- Read-only collectors emit explicit read-only findings.
- Analysis errors block readiness with `score_status=BLOCKED_BY_ANALYSIS_ERROR`.
- JSON output keeps a stable top-level contract.
- Root-cause hypotheses are deterministic and evidence-backed.
- No unintended untracked or unstaged files are present before release.

## Verification Commands

Run the full test suite:

```bash
python3 -m pytest -q
```

Run the release gate. Add `--require-helm` in CI or release environments where Helm rendering must be validated end to end.

```bash
python3 scripts/module1_release_check.py
```

Run the static supported examples:

```bash
python3 -m beacon.cli readiness static examples/supported --no-html --no-open-report
```

For release CI, install the Helm CLI before treating this command as a full Helm rendering validation. If Helm is not installed, Beacon should emit `helm.render.unavailable` and block readiness instead of silently skipping chart analysis.

Run the all-domain runtime snapshot:

```bash
python3 -m beacon.cli readiness snapshot examples/supported/runtime/all-runtime.yaml --no-html --no-open-report --output json
```

Run combined all-domain readiness across static and runtime inputs:

```bash
python3 -m beacon.cli readiness all --static-path examples/supported --snapshot examples/supported/runtime/all-runtime.yaml --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml --no-html --no-open-report --output json
```

Run combined all-domain diagnostics:

```bash
python3 -m beacon.cli diagnose all --snapshot examples/supported/runtime/all-runtime.yaml --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml --no-html --no-open-report --output json
```

Run the OpenTelemetry sample:

```bash
python3 -m beacon.cli readiness opentelemetry examples/supported/opentelemetry/checkout-otel.yaml --no-html --no-open-report --output json
```

Run the Prometheus sample. In local development this may intentionally produce query failures if no Prometheus server is available; that should block readiness rather than silently pass.

```bash
python3 -m beacon.cli readiness prometheus examples/supported/prometheus/platform-prometheus.yaml --timeout 1 --no-html --no-open-report --output json
```

Optional live read-only checks:

```bash
python3 -m beacon.cli readiness kafka --bootstrap-server localhost:9092 --no-html --no-open-report
python3 -m beacon.cli readiness kubernetes --namespace default --no-html --no-open-report
```

## JSON Contract

Readiness JSON output should keep these top-level fields:

- `score`
- `score_status`
- `readiness_summary`
- `findings`

`readiness_summary` should include:

- `score`
- `score_status`
- `production_decision`
- `survivability`
- `categories`
- `primary_risk_area`
- `top_reasons`
- `next_best_actions`
- `root_cause_hypotheses`

Each finding should include:

- `rule_id`
- `severity`
- `title`
- `impact`
- `recommendation`
- `file`
- `evidence`

Root-cause hypotheses should include:

- `correlation_id`
- `title`
- `confidence`
- `score`
- `evidence`
- `matched_rule_ids`
- `recommendation`

## Release Decision

Module 1 is releasable when the verification commands pass, registered rule metadata is complete, and the release surface above is documented as the supported boundary.

The next product move after Module 1 is deeper Module 2 runtime intelligence: stronger live collectors, deployment correlation, and ranked cross-system root-cause narratives across Kafka, Kubernetes, Prometheus, OpenTelemetry, APIs, databases, and storage.
