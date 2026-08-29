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
