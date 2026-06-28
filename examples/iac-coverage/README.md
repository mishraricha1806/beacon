# IaC Coverage Readiness Example

This example demonstrates unmanaged cloud resource detection without live cloud
access.

Beacon compares:

- `aws-inventory.json`: cloud inventory export
- `aws-config-inventory.json`: AWS Config-style `configurationItems` export
- `steampipe-rows.json`: Steampipe/CloudQuery-style row export
- `terraform-state.json`: Terraform state-style JSON
- `states/`: directory of Terraform state files for larger-org indexing
- `terraform-workspaces.yaml`: manifest of state files/workspaces
- `owners.yaml`: optional ownership metadata

Run:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

Expected outcome:

```text
Production Decision: NOT READY

Top risks include:
- unmanaged OpenSearch domain
- missing owner metadata
- recent cost/activity on unmanaged infrastructure
- public exposure on unmanaged infrastructure
- sensitive unmanaged storage/search resources
```

AWS Config-style export:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-config-inventory.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --environment prod \
  --no-html \
  --no-open-report
```

Steampipe/CloudQuery-style rows:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/steampipe-rows.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --environment prod \
  --no-html \
  --no-open-report
```

Multiple Terraform state files:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --terraform-state-dir examples/iac-coverage/states \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```

Manifest of Terraform states or workspaces:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --state-manifest examples/iac-coverage/terraform-workspaces.yaml \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report
```
