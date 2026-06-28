# Beacon, OPA, Sentinel, And Guardrails

Beacon does not replace OPA, Sentinel, admission controllers, or policy-as-code
guardrails.

Those tools are the right layer for deterministic enforcement:

```text
Deny this deployment if replication_factor < 3.
Deny this pod if privileged = true.
Deny this Terraform plan if public database access is enabled.
```

Beacon focuses on release readiness and operational survivability:

```text
Given the infrastructure config, runtime signals, ownership metadata,
recovery posture, and environment profile, is this system ready to go to
production?
```

## Difference In One Line

```text
OPA/Sentinel enforce individual policies.
Beacon explains release readiness across many operational signals.
```

## Where OPA/Sentinel Fit Best

- hard allow/deny controls
- admission-time enforcement
- Terraform plan gates
- organization-wide mandatory policy
- compliance controls that should not be subjective

## Where Beacon Fits Best

- grouped readiness assessment before release
- operational-risk scoring
- duplicate finding suppression and root-cause grouping
- environment-aware interpretation such as dev/test/prod
- static config plus runtime signal correlation
- next-best-action reporting for engineers

## Why Readiness Packs Exist

Beacon readiness packs make the checks visible.

Instead of asking engineers to trust a black-box binary first, packs show the
rule IDs, intent, and scope behind a readiness domain. For example:

```bash
python3 -m beacon.cli packs show kafka-production-readiness
python3 -m beacon.cli packs rules kafka-production-readiness
```

The intended model is:

```text
Beacon engine
= normalize inputs + run deterministic checks + group risks + score readiness + report

Readiness packs
= inspectable rule groupings that teams can review, adapt, and debate
```

## Example

OPA can catch:

```text
Kafka topic replication_factor < 3
```

Beacon can explain:

```text
This release is not ready because replication risk, weak ISR posture,
unbounded retention, missing ownership, and unsafe Schema Registry
compatibility combine into poor recovery readiness.
```

That does not make Beacon better than policy-as-code. It makes Beacon a
different layer: a readiness and operational reasoning layer that can sit next
to policy-as-code.

