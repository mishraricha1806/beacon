# Readiness Pack Manifest Contract

Beacon readiness packs are governed, inspectable collections of deterministic rule IDs. They do not execute arbitrary code and are not a second rule engine.

## Manifest v1

Every `pack.yaml` declares:

```yaml
schema_version: 1.0.0
id: payments-production-readiness
name: Payments Production Readiness
version: 1.0.0
status: preview
owner: payments-platform
support_tier: experimental

engine_compatibility:
  min_version: 0.1.0
  max_version_exclusive: 0.2.0

domains:
  - kubernetes
  - kafka

non_goals:
  - Mutating production infrastructure

fixtures:
  - path: examples/payments-readiness.yaml
    expected_rule_ids:
      - k8s.workload.probes.missing

deprecation:
  notice: null
  removal_after: null
  replacement: null

rules:
  - rule_id: k8s.workload.probes.missing
    intent: Workloads must expose safe traffic-routing and recovery signals.
```

The machine-readable schema is shipped as `beacon/schemas/readiness-pack-v1.schema.json`.

## Lifecycle

- `preview` packs may change within their current major version and normally use `experimental` support.
- `stable` packs require fixtures and compatibility testing. Breaking manifest or semantic changes require a new major pack version.
- `deprecated` packs must declare `deprecation.removal_after`; a replacement should be named when one exists.

`support_tier` communicates operational ownership:

- `experimental`: best-effort evaluation, not recommended as an organization-wide required gate;
- `supported`: owned and maintained for normal production use;
- `critical`: stricter support expectations for organization-standard release gates.

## Validation

Validate all discovered packs:

```bash
beacon packs validate
```

Validate one pack against a planned Beacon engine version:

```bash
beacon packs validate \
  --pack payments-production-readiness \
  --engine-version 0.1.10 \
  --output json
```

Validation fails when required governance fields are missing, semantic versions are invalid, the engine falls outside the supported range, fixture paths are missing, rule metadata cannot be resolved, or lifecycle requirements are incomplete.

Pack discovery gives precedence to `BEACON_PACKS_DIR`, then the current repository's `packs/` directory, then bundled packs. This allows an organization to intentionally replace a bundled pack ID with a governed internal definition.

## Promotion checklist

Before changing a pack from `preview` to `stable`:

1. Assign an accountable owner and supported service tier.
2. Define the minimum and maximum compatible Beacon engine versions.
3. Add representative fixtures and expected rule IDs.
4. Confirm every rule has metadata, intent, remediation guidance, and deterministic evidence.
5. Run contract, compatibility, performance, and security checks.
6. Document upgrade and deprecation behavior.
7. Pilot the pack with multiple service teams and review false-positive rates.

Pack validation proves structural readiness. Human owners still decide whether the pack's policy is appropriate for a service tier and environment.
