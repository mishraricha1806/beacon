# Beacon Readiness Packs

Readiness packs make Beacon's checks visible and discussable.

Beacon is still the runner, normalizer, scorer, reporter, and UI. Packs are the
inspectable rule groupings behind that experience. They let teams review which
signals are used, adapt them to local standards, and debate operational
judgement without treating Beacon as a black box.

## Available Packs

| Pack | Purpose |
| --- | --- |
| `kafka-production-readiness` | Kafka topic, broker, client, Schema Registry, ACL, runtime, and replay readiness checks. |

## Commands

```bash
python3 -m beacon.cli packs list
python3 -m beacon.cli packs show kafka-production-readiness
python3 -m beacon.cli packs rules kafka-production-readiness
```

## Why Packs?

OPA and Sentinel are strong policy-enforcement layers. Beacon packs are not a
replacement for that. They are a release-readiness layer:

- group related operational risks
- connect static config and runtime signals
- explain business impact
- rank what to fix first
- keep the underlying checks visible

