# IaC Coverage Readiness Pack

This pack defines the checks Beacon uses to answer:

```text
What cloud resources exist outside Terraform state, and what risk do they create?
```

It is intentionally file-based for the first MVP. Beacon compares cloud
inventory exports, Terraform state JSON, and optional owner metadata. It accepts
Beacon's simple `resources` shape, AWS Config-style `configurationItems`, AWS
Resource Explorer-style `Resources`, and Steampipe/CloudQuery-style `rows`. It
does not connect to cloud accounts or import resources into Terraform.

## What This Pack Covers

- unmanaged cloud resources
- missing owner metadata
- unmanaged resources with recent cost/activity
- unmanaged resources with public exposure
- sensitive unmanaged databases, search clusters, storage, and platform resources

## Example

```bash
python3 -m beacon.cli packs show iac-coverage-readiness
python3 -m beacon.cli packs rules iac-coverage-readiness
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

Other supported example inputs:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-config-inventory.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --environment prod \
  --no-html \
  --no-open-report

python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/steampipe-rows.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --environment prod \
  --no-html \
  --no-open-report
```

## Relationship To Drift Detection

Terraform drift detection asks:

```text
Did a managed resource change outside Terraform?
```

Beacon IaC coverage asks:

```text
What important cloud resources exist outside Terraform entirely, and what risk
do they create?
```
