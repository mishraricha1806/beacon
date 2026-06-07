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
environment: prod
criticality: high

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
