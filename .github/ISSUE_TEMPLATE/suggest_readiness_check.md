---
name: Suggest a readiness check
about: Propose a Kafka, Kubernetes, Terraform, cloud, CI/CD, or runtime readiness check
title: "[Readiness check]: "
labels: readiness-check
assignees: ""
---

## What should Beacon check?

Describe the readiness risk or operational anti-pattern.

Example:

```text
Kafka topics with retention.ms=-1 should be flagged for production clusters.
```

## Which domain does this apply to?

- [ ] Kafka
- [ ] Kubernetes
- [ ] Terraform
- [ ] Helm
- [ ] Cloud/IAM/storage
- [ ] CI/CD
- [ ] Runtime diagnostics
- [ ] Flow intelligence
- [ ] Other:

## Why does it matter in production?

What incident, outage, cost problem, security risk, or recovery problem can this prevent?

## What evidence should Beacon inspect?

Examples:

- Terraform resource field
- Kubernetes YAML field
- Kafka topic/broker/client config
- Runtime metric/snapshot
- Schema Registry setting
- ACL export

## Suggested severity

- [ ] Critical
- [ ] High
- [ ] Medium
- [ ] Low
- [ ] Depends on environment

## Environment context

Should this behave differently for dev/test/staging/prod?

## Any example config?

Paste a small safe example if you can. Please do not include secrets, real tokens, private hostnames, or production data.

