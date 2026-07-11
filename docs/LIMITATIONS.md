# Beacon Limitations

Beacon is a local readiness checker. It is useful when it has enough
configuration, snapshot, and ownership evidence to evaluate a release risk. It
does not know everything about a live environment.

## What Beacon Does Not Do

Beacon does not:

- mutate infrastructure
- apply Terraform
- change Kubernetes resources
- produce or consume Kafka messages
- alter Kafka topics, ACLs, or consumer offsets
- replace OPA, Sentinel, admission controllers, or cloud-native policy tools
- discover a complete live service graph by itself
- prove root cause from one metric such as consumer lag
- guarantee that a system is safe to run in production

## Known Evidence Gaps

Beacon lowers confidence or emits coverage gaps when:

- Terraform plan values are unknown until apply
- topology metadata is missing
- owner, runbook, or service catalog metadata is missing
- runtime snapshots are stale or partial
- Kafka lag exists without producer, consumer, broker, or downstream evidence
- Kubernetes manifests do not show cluster admission policy or namespace policy
- cloud inventory does not include tags, activity, or dependency context

## Terraform Unknown-After-Apply

Terraform plans often contain values that are only known after apply:

- endpoint URLs
- subnet IDs
- security group IDs
- broker addresses
- generated resource IDs
- DNS names

Beacon treats those as unresolved evidence. It should not invent strong
dependency edges from unknown values. For pre-apply scans, Beacon reports
intent-based readiness. For stronger evidence, rerun Beacon after apply with
Terraform state and live snapshots.

## Runtime Diagnostics

Runtime diagnosis is deterministic and evidence-based. If Beacon sees Kafka lag
but no producer rate, broker health, consumer processing latency, or downstream
database/API signal, it should report a telemetry gap instead of claiming a
specific root cause.

## Custom Rules

Readiness packs are inspectable, and policy files can waive findings or adjust
severity. New executable rule logic is currently defined inside Beacon's
registered rule system.

