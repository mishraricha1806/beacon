# Static Production Readiness Demo

This is the first-user Beacon demo.

It avoids live clusters, secrets, topology modeling, and environment profiles.
The user only needs infrastructure/config files and five minutes.

## Run It

```bash
scripts/demo_readiness_static.sh
```

The demo scans:

```text
examples/bad-infra
```

It generates:

```text
reports/report.html
reports/readiness-demo/bad-infra-readiness.json
```

It also runs:

```bash
python3 scripts/ui_smoke_check.py
```

That starts the local Beacon UI handler on a temporary port, loads the homepage,
uploads the same bad-infra Kafka config through `/api/beacon`, and verifies the
release-gate response.

## Product Story

Use this positioning:

```text
Beacon helps teams check production readiness before release.
```

Do not lead with environment modeling or full operational intelligence. The
first user experience should be:

```text
Run Beacon on your infra/config.
Get a production decision, score, risks, and next actions.
```

## What To Show

Open:

```text
reports/report.html
```

The first card answers:

- Is this production ready?
- Why not?
- What should I fix first?
- What is the business risk?

The UI smoke check verifies the same first-card contract from the browser-facing
API path.

Then show:

- Production Readiness Score
- Top Reasons
- Next Best Actions
- Business Risk Categories
- Grouped Root-Cause Risks
- Findings

## Demo Command

```bash
python3 -m beacon.cli readiness static examples/bad-infra --no-open-report
```

Expected story:

```text
Production Decision: NOT READY

Top risks include:
- Kafka replication factor 1
- oversized Kafka message configuration
- weak object storage public-access protection

Recommended action:
Fix critical resiliency and operational-safety risks before production.
```

## Why This Is The Right First Demo

Early users do not need to:

- connect to Kafka
- provide certificates
- model dependencies
- define a full environment profile
- upload secrets

They can scan files they already have and immediately see whether the release is
safe enough for production.
