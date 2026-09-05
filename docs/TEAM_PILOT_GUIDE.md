# Beacon Team Pilot Guide

Beacon should prove repeatable value as a deterministic CLI gate before a centralized control plane is built. This guide defines a small, reversible pilot for service teams.

## Product boundary

Beacon reads repository and explicitly configured runtime evidence. It does not mutate infrastructure, replace telemetry stores, or approve a release. Findings, scores, and suggested fixes are deterministic outputs from inspectable rules. A named human owner remains accountable for each release decision.

AI may be added later as an optional explanation layer. It must cite the evidence already present in Beacon artifacts, expose uncertainty, and never create evidence, change a score, or independently pass or fail a gate.

## Select pilot teams

Choose three to five teams with different operating profiles:

- one mature, high-criticality service with reliable ownership and telemetry;
- one typical production service with known operational debt;
- one lower-criticality service that can test onboarding usability;
- optionally, one event-driven or Kafka-heavy service and one Kubernetes-heavy service.

Each team names a service owner and an SRE or platform partner. Avoid using the first pilot as an executive compliance scorecard; the goal is to calibrate evidence, rules, and workflow usability.

Before enabling a gate, record every pilot service in `beacon.yaml` with its tier, owner, and on-call route. Beacon derives a recommended default threshold from the strictest service tier but never overrides an explicit `ci.fail_on`. Review the emitted `service_governance` evidence and resolve missing ownership for tier-0 and tier-1 services before making the check required.

## Add the reusable CI action

Create `.github/workflows/beacon-readiness.yml` in the service repository:

```yaml
name: Beacon readiness

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  readiness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: beacon
        uses: mishraricha1806/beacon/.github/actions/beacon-readiness@v1
        with:
          scan-path: .
          environment: prod
          fail-on: high
          # Optional after the first accepted baseline is stored in the repository:
          # baseline-evidence: .beacon/baseline-release-evidence.json

      - name: Preserve Beacon evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: beacon-readiness-${{ github.run_id }}
          path: beacon-reports/
          if-no-files-found: error
          retention-days: 30
```

Pin the action to an immutable commit SHA for production use. The `@v1` reference above is intentionally readable for initial evaluation.

## Rollout stages

1. **Observe for two weeks.** Run on pull requests without making Beacon a required check. Record false positives, missing evidence, runtime, and onboarding effort.
2. **Calibrate with owners.** Assign every blocking rule an owner, rationale, remediation path, and documented exception policy. Remove or downgrade rules that cannot support their conclusion with evidence.
3. **Gate only proven signals.** Make the workflow required only after the team accepts the rule set and evidence quality. Start with critical findings or analysis errors; tighten thresholds deliberately.
4. **Compare releases.** Preserve `beacon-release-evidence.json` and compare baselines so teams can see new and resolved risks instead of treating the score as an isolated number.
5. **Review the pilot.** Continue only if the CLI produces actionable findings with acceptable noise and low operational burden.

## Evidence and governance contract

The report and release-evidence artifacts declare `schema_version`, `generated_at`, and the Beacon engine version. Consumers must reject unsupported major schema versions and tolerate additive fields within a supported major version.

The reusable action always writes four primary artifacts under `beacon-reports/`, even when the configured gate fails:

- `beacon-report.json` - the complete versioned Beacon report;
- `beacon-release-evidence.json` - the compact governed release record;
- `beacon-results.sarif` - SARIF 2.1.0 findings with stable fingerprints and waiver suppressions;
- `beacon-results.xml` - JUnit results using the configured `fail-on` threshold.

When `baseline-evidence` is provided, it also writes:

- `beacon-comparison.json` - a machine-readable new/resolved risk comparison;
- `beacon-comparison.md` - a safe Markdown summary suitable for a pull-request or workflow summary.

Accept a new baseline only through normal code review with the service owner. A baseline is historical evidence, not a waiver: existing risks remain visible, and newly introduced blockers still fail according to `fail-on`.

Teams running the CLI directly can produce the same integration files:

```bash
beacon readiness static . \
  --environment prod \
  --no-html \
  --no-open-report \
  --output json \
  --fail-on high \
  --evidence-output beacon-reports/beacon-release-evidence.json \
  --sarif-output beacon-reports/beacon-results.sarif \
  --junit-output beacon-reports/beacon-results.xml
```

SARIF and JUnit are presentation formats, not independent decision engines. The versioned release-evidence artifact remains the auditable source for Beacon's decision, evidence quality, waivers, and human review checklist.

The action also writes `beacon-pack-validation.json` and fails with an analysis error if a discovered readiness-pack manifest is malformed, incompatible with the running Beacon engine, missing rule metadata or fixtures, or violates its lifecycle policy.

For each gated release, retain:

- the immutable source revision and workflow run identifier;
- the Beacon report and release-evidence artifacts;
- the policy bundle and readiness-pack versions;
- waivers with owner, scope, reason, approval, and expiry;
- the accountable human decision and any follow-up work item.

Credentials must remain short-lived and read-only. Do not place secrets in scanned files, action inputs, reports, or uploaded evidence.

## Pilot success measures

Review these measures after four to six weeks:

- median onboarding time and CI runtime;
- percentage of findings accepted as valid by service owners;
- percentage of blocking findings with an owner and actionable remediation;
- new risks caught before deployment and material risks resolved;
- waiver count, age, and expiry compliance;
- analysis-error rate and evidence coverage gaps;
- team willingness to keep the check enabled.

Do not proceed to a central control plane until several teams can run the CLI independently, artifacts remain contract-compatible, security gates are green, and the pilot demonstrates repeatable release decisions rather than a vanity score.
