# Observability Production-Readiness Review

Beacon can review whether a service has enough observable operating evidence to
support a release and incident response. The review is deterministic, read-only,
and evidence-bound. It does not create SLOs, dashboards, alerts, or telemetry.

## Review contract

The input contract is published at
`beacon/schemas/observability-review-v1.schema.json`. Each document declares:

- a schema version, capture timestamp, freshness policy, service, owner, and tier;
- measurable SLOs, remaining error budget, and paired burn-rate alert windows;
- alert ownership, routing, severity, and runbook references;
- dashboard coverage for availability, latency, traffic, errors, and saturation;
- metrics, logs, traces, propagation, correlation, and sampling evidence;
- active-series and monthly-cost budgets;
- sensitive fields found by an upstream telemetry inspection process;
- owned synthetic checks for customer journeys;
- incident timelines, deployment windows, and comparable historical snapshots.

Use the maintained example as a starting point:

```bash
cp examples/supported/observability/checkout-observability.yaml observability-review.yaml
```

Production evidence should normally use a 24- to 48-hour maximum age. The
example uses a deliberately long age only so the packaged fixture remains
reproducible.

## Run the review

```bash
beacon readiness observability observability-review.yaml \
  --environment prod \
  --no-html \
  --no-open-report \
  --output json \
  --ci \
  --fail-on high \
  --evidence-output beacon-reports/beacon-release-evidence.json \
  --sarif-output beacon-reports/beacon-results.sarif \
  --junit-output beacon-reports/beacon-results.xml
```

Combine it with infrastructure and runtime evidence:

```bash
beacon readiness all \
  --static-path . \
  --observability-review observability-review.yaml \
  --environment prod
```

The reusable GitHub Action accepts the same file:

```yaml
- uses: mishraricha1806/beacon/.github/actions/beacon-readiness@<immutable-commit-sha>
  with:
    scan-path: .
    observability-review: observability-review.yaml
    environment: prod
    fail-on: high
```

## Evidence semantics

Every conclusion emitted by this reviewer contains:

- `confidence`: how strongly the declared evidence supports the conclusion;
- `freshness`: `CURRENT`, `STALE`, or `UNKNOWN`;
- `evidence_bound: true`: confirmation that Beacon did not invent external evidence.

Stale review evidence is an analysis error because it cannot safely support a
release decision. Temporal deployment correlation is medium-confidence and does
not claim causality. Sensitive-field detection consumes declarations from an
upstream scanner; Beacon does not inspect raw production telemetry in this mode.

## Rollout policy

Run the review in observe-only mode first. Service owners must validate the
meaning, thresholds, data sources, and remediation for every proposed blocking
rule. A missing declaration means “not evidenced,” not necessarily “absent.”
Only make a rule a required gate after its evidence has acceptable freshness,
coverage, and false-positive performance for that service.

The governed rule inventory is in the
`observability-production-readiness` pack. Inspect it with:

```bash
beacon packs show observability-production-readiness
beacon packs rules observability-production-readiness
beacon packs validate
```

## Product boundary

This capability is a local CLI review, not an observability backend or shared
control plane. Beacon does not ingest raw telemetry continuously, store secrets,
send notifications, approve releases, or mutate monitoring systems. A human
owner remains accountable for every release decision and waiver.
