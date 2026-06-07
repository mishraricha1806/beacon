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

report:
  format:
    - terminal
    - html
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
