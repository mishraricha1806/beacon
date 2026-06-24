# Project-Local Beacon Config

Beacon supports project-local configuration so teams can run production
readiness checks without long command lines.

## Create Config

```bash
beacon init
```

This creates:

```text
beacon.yaml
reports/
```

## Discovery

Beacon discovers config by walking from the current directory upward:

```text
beacon.yaml
beacon.yml
.beacon.yaml
```

## Example

```yaml
project: loan-service
environment:
  name: prod-us-east
  profile: prod
  criticality: high
  owner: lending-platform
  rto: 30m
  rpo: 5m
  business_flows:
    - loan-application
  services:
    - loan-api
    - loan-decision-worker
  dependencies:
    kafka:
      clusters:
        - lending-events
    kubernetes:
      clusters:
        - prod-us-east
    database:
      instances:
        - loan-db

readiness:
  include:
    - ./infra
    - ./k8s
    - ./kafka
  exclude:
    - ./reports
    - ./.terraform

intelligence:
  context: ./platform-context.yaml

policy:
  rules:
    kafka.topic.owner.missing:
      severity: LOW
  waivers:
    - rule_id: kafka.topic.partitions.low
      resource_pattern: "*.retry"
      reason: Retry topics intentionally preserve strict ordering.
      expires: 2026-12-31
      severity: INFO

ci:
  enabled: false
  fail_on: critical

report:
  format:
    - terminal
    - html
  evidence_output: ./reports/beacon-evidence.json
  open: false

live:
  runtime:
    snapshot: ./runtime/all-runtime.yaml
    flow: ./runtime/flow-runtime.yaml
    deployment_events: ./deployments/events.yaml
  kafka:
    access_config: ./kafka/access-profiles.yaml
    acls: ./kafka/acls.yaml
    history: ./kafka/history.yaml
  schema_registry:
    config: ./kafka/schema-registry.yaml

tasks:
  prod-check:
    command: readiness
    environment: prod

  kafka-incident-demo:
    command: diagnose kafka-runtime
    path: ./runtime/kafka-incident.yaml
```

## Commands

Run configured readiness:

```bash
beacon readiness
```

Check setup:

```bash
beacon doctor
```

Run a named workflow:

```bash
beacon run prod-check
beacon run kafka-incident-demo
```

## Policy, Waivers, And CI Gates

Beacon policies let teams adapt the readiness gate to real environment context
without hiding risk.

Built-in readiness profiles:

```text
dev              relaxed developer/sandbox profile
test             shared test profile
nonprod          generic non-production profile when the exact tier is unknown
staging          production-like pre-prod profile
prod             strict production profile
mission-critical stricter production profile for high-criticality systems
```

When `environment` has both `name` and `profile`, Beacon uses `profile` for
policy interpretation and keeps `name` in the environment-readiness model:

```yaml
environment:
  name: prod-us-east
  profile: prod
  criticality: high
```

Use `policy.rules` to disable or change severity for a rule:

```yaml
policy:
  rules:
    kafka.topic.owner.missing:
      severity: LOW
    kafka.topic.retention_bytes.missing:
      enabled: false
```

Use `policy.waivers` for accepted exceptions. Waived findings stay visible in
the report, keep their reason and expiry date, and default to `INFO` severity:

```yaml
policy:
  waivers:
    - rule_id: kafka.topic.partitions.low
      resource: orders.retry
      reason: Ordered retry stream; one partition is intentional.
      expires: 2026-12-31
```

Use `ci` to make Beacon behave like a release gate:

```yaml
ci:
  enabled: true
  fail_on: high
```

Exit codes:

```text
0 = configured gate passed
1 = readiness risk crossed the configured severity threshold
2 = analysis was blocked by collector, parsing, or input errors
```

You can also enable CI mode without changing `beacon.yaml`:

```bash
beacon readiness --ci --fail-on high
beacon readiness static ./infra --ci --fail-on critical
beacon readiness all --static-path ./infra --ci --fail-on high
```

Copy-paste examples for GitHub Actions, GitLab CI, Jenkins, and Docker are in
[CICD_INTEGRATION.md](CICD_INTEGRATION.md).

## Release Evidence Pack

Every readiness summary includes a release evidence pack. It is designed for PRs,
change tickets, release approvals, and CI logs.

Get it from JSON output:

```bash
beacon readiness --output json
beacon readiness static ./infra --output json
beacon readiness all --static-path ./infra --output json
```

Or write the evidence pack directly to a separate file:

```bash
beacon readiness --evidence-output ./reports/beacon-evidence.json
beacon readiness static ./infra --evidence-output ./reports/beacon-evidence.json
```

Compare two evidence packs to see whether a release improved or regressed:

```bash
beacon compare ./reports/beacon-evidence-before.json ./reports/beacon-evidence-after.json
beacon compare ./reports/beacon-evidence-before.json ./reports/beacon-evidence-after.json --output json
```

Beacon reports score delta, decision changes, new production blockers, and
resolved production blockers.

The evidence pack contains:

```text
decision
score
environment
domains covered
evidence files scanned
blocking risks
major risks
waived risks
suppressed duplicate findings
next best actions
coverage gaps
```

In JSON, read:

```text
readiness_summary.release_evidence
```

## Safety

`beacon run` only supports known Beacon workflows. It does not execute arbitrary
shell commands from `beacon.yaml`.

## Full Environment Readiness

For full environment readiness, define:

- environment name/profile/criticality
- owner and recovery targets
- business flows
- services
- dependency domains
- static readiness paths
- runtime/live evidence profiles

Then `beacon readiness` produces both:

```text
Environment Readiness
Distributed System Readiness
```

The environment model helps Beacon answer broader questions:

```text
Which business flow is at risk?
Which dependency domains are covered?
Which domains are blocked or high risk?
What evidence is still missing before this environment can be trusted?
```
