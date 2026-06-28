# IaC Coverage Readiness

IaC coverage readiness is Beacon's file-based capability for finding cloud
resources that exist outside Terraform state or approved infrastructure-as-code
ownership.

This is different from Terraform drift detection.

```text
Terraform drift detection asks:
"Did a managed resource change outside Terraform?"

Beacon IaC coverage asks:
"What important cloud resources exist outside Terraform entirely, and what
risk do they create?"
```

## Problem

Large cloud estates often contain resources that were never captured in
Terraform:

- resources created manually during incidents
- forgotten workloads in dormant accounts
- experiments that nobody owns anymore
- production resources with no Terraform state entry
- infrastructure with cost, network exposure, or data risk but no owner

That creates production-readiness risk because teams cannot reliably answer:

- Who owns this resource?
- Is it still used?
- Is it safe to delete?
- Should it be imported into Terraform?
- Does it have dangerous network, IAM, backup, or data posture?
- What is the blast radius if it fails or is removed?

## Beacon's Role

Beacon should not blindly import everything into Terraform.

Beacon should:

```text
Detect unmanaged resources
Classify them
Rank their risk
Recommend disposition
```

Disposition examples:

- import into Terraform
- delete after validation
- tag and monitor
- move to a legacy or exception workspace
- owner review required
- do not touch yet because blast radius is unknown

## Current MVP

The first implementation is file-based. It does not require live AWS/GCP access.

Inputs:

- cloud inventory export
- AWS Config-style `configurationItems` export
- AWS Resource Explorer-style `Resources` export
- Steampipe or CloudQuery-style `rows` export
- Terraform state JSON
- ownership metadata
- optional cost/activity export
- optional network/security metadata

Example command:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --terraform-state examples/iac-coverage/terraform-state.json \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod
```

For larger organizations, Beacon does not need to compare inventory against one
state file only. It can build a managed-resource index across many Terraform
state files.

Directory mode:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory exports/aws-config-prod.json \
  --terraform-state-dir exports/terraform-states \
  --owners exports/owners.yaml \
  --environment prod
```

Manifest mode:

```bash
python3 -m beacon.cli readiness iac-coverage \
  --cloud-inventory exports/aws-config-prod.json \
  --state-manifest exports/terraform-workspaces.yaml \
  --owners exports/owners.yaml \
  --environment prod
```

Example manifest:

```yaml
terraform_states:
  - path: states/platform-prod.tfstate
    workspace: platform-prod
  - path: states/payments-prod.tfstate
    workspace: payments-prod
  - path: states/data-prod.tfstate
    workspace: data-prod
```

This is the intended large-org direction: cloud inventory compared against a
combined Terraform-managed resource index, then grouped by account, region,
service, owner, and risk.

Example finding:

```text
OpenSearch domain exists in AWS but not in Terraform state
Severity: High

Evidence:
- account: prod-shared-services
- region: us-east-1
- resource: search-claims-archive
- owner tag: missing
- cost activity: detected in last 30 days
- terraform state match: none

Recommendation:
Owner review required before import or deletion. Classify dependency and
business criticality, then import into Terraform or document an exception.
```

## Current Finding Types

Beacon currently emits:

- `iac_coverage.resource.unmanaged`
- `iac_coverage.resource.owner_missing`
- `iac_coverage.resource.active_unmanaged`
- `iac_coverage.resource.public_unmanaged`
- `iac_coverage.resource.sensitive_unmanaged`

## Future Collectors

Beacon can already consume file exports shaped like:

- AWS Resource Explorer
- CloudQuery
- Steampipe

Beacon can later add live or direct collectors for:

- AWS Config aggregator
- GCP Cloud Asset Inventory
- Azure Resource Graph
- Terraform Cloud/Enterprise state
- Backstage catalog
- CMDB or internal ownership registry

Beacon should sit above those tools:

```text
CloudQuery / Steampipe / AWS Config = collect and query inventory
Beacon = interpret inventory as readiness risk and recommend action
```

## Readiness Categories

IaC coverage should contribute to:

- operational safety
- governance
- recovery readiness
- security/IAM readiness
- cost and capacity risk
- blast-radius analysis

## Readiness Pack

```text
iac-coverage-readiness
```

It includes checks for:

- live resource missing from Terraform state
- resource missing owner/application tags
- resource has cost activity but no ownership metadata
- resource has public network exposure and no Terraform owner
- database/search/storage resource missing backup or deletion protection
- resource exists in dormant account but has recent activity
- unmanaged resource attached to production VPC, IAM role, or service path
