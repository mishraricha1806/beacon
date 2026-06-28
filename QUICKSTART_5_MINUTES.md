# Beacon 5-Minute Quickstart

Beacon helps answer:

```text
Is this system production ready, and what should we fix first?
```

This quickstart uses Docker and safe example files. You do not need Python,
source-code access, cloud credentials, Kafka credentials, or production data.

## 1. Pull Beacon

```bash
docker pull ghcr.io/mishraricha1806/beacon:latest
```

For quick evaluation, `:latest` is fine. For safer and reproducible internal
usage, pin the image by digest:

```bash
docker buildx imagetools inspect ghcr.io/mishraricha1806/beacon:latest

docker run --rm ghcr.io/mishraricha1806/beacon@sha256:<digest> --help
```

## 2. Run The Local UI

```bash
docker run --rm -p 8765:8765 \
  ghcr.io/mishraricha1806/beacon:latest \
  ui --host 0.0.0.0 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

Use `0.0.0.0` only in the Docker command. Use `127.0.0.1` or `localhost` in
the browser.

If port `8765` is busy:

```bash
docker run --rm -p 8777:8765 \
  ghcr.io/mishraricha1806/beacon:latest \
  ui --host 0.0.0.0 --port 8765
```

Then open:

```text
http://127.0.0.1:8777/
```

## 3. Run A CLI Readiness Scan

Run this from a folder that contains the Beacon example files:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/examples/product-readiness/distributed-infra-risk \
  --environment prod \
  --no-html \
  --no-open-report
```

If the example path does not exist, mount your examples folder directly:

```bash
docker run --rm \
  -v "/absolute/path/to/examples:/workspace/examples:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/examples/product-readiness/distributed-infra-risk \
  --environment prod \
  --no-html \
  --no-open-report
```

## 4. Expected Result

The demo should produce a production-readiness decision similar to:

```text
Production Decision: NOT READY

Top risks include:
- Kubernetes admission/RBAC/secret posture issues
- Kafka client/broker security posture issues
- database recovery/encryption gaps
- broad IAM admin policy attachment
- object-storage recovery gaps
```

Beacon should not only list raw findings. It should group repeated risks,
explain why they matter, and recommend what to fix first.

You should also see an `Operational Decisions` section when the scan has enough
evidence. That section is Beacon's decision layer:

```text
Operational Decisions
1. Remove public exposure before approving production release
   Target: security
   Safety: safe
   Confidence: high
   Do not do: do not waive public exposure without an approved exception
```

This is different from a raw policy failure. Beacon is trying to answer:

```text
What should an engineer do first, and what should they avoid doing blindly?
```

## 5. Optional: Check IaC Coverage

Beacon can also detect cloud resources that exist outside Terraform state using
local export files:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness iac-coverage \
  --cloud-inventory /workspace/project/examples/iac-coverage/aws-inventory.json \
  --terraform-state /workspace/project/examples/iac-coverage/terraform-state.json \
  --owners /workspace/project/examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

This does not connect to AWS. It compares local inventory and Terraform state
exports.

The IaC coverage input can use Beacon's simple `resources` shape, AWS
Config-style `configurationItems`, AWS Resource Explorer-style `Resources`, or
Steampipe/CloudQuery-style `rows`.

For larger orgs, use many Terraform states instead of one state file:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness iac-coverage \
  --cloud-inventory /workspace/project/exports/aws-config-prod.json \
  --terraform-state-dir /workspace/project/exports/terraform-states \
  --owners /workspace/project/exports/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

Or provide a manifest:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness iac-coverage \
  --cloud-inventory /workspace/project/exports/aws-config-prod.json \
  --state-manifest /workspace/project/exports/terraform-workspaces.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

## 6. Inspect The Checks Before Trusting Them

Beacon includes inspectable readiness packs.

```bash
docker run --rm ghcr.io/mishraricha1806/beacon:latest packs list

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  kafka-production-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs rules \
  kafka-production-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  kubernetes-production-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  cloud-production-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  cloud-azure-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  cloud-gcp-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  terraform-aws-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  distributed-system-production-readiness

docker run --rm ghcr.io/mishraricha1806/beacon:latest packs show \
  iac-coverage-readiness
```

This is intentional. Beacon should be transparent: you should be able to see
which checks exist and challenge them.

## 7. What Beacon Is Not

Beacon does not replace:

- OPA
- Sentinel
- admission controllers
- Prometheus/Grafana
- log platforms
- observability systems

Those tools enforce policies and observe systems.

Beacon explains release readiness and operational risk across many signals.

## 8. Share Feedback

Feedback is the goal right now.

Open an issue:

```text
https://github.com/mishraricha1806/beacon/issues/new/choose
```

Useful feedback:

- suggest a readiness check
- challenge an existing check
- share a production-readiness or runtime-diagnostics use case
