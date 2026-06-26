# Terraform AWS Readiness Pack

This pack defines the AWS/Terraform checks Beacon uses to answer:

```text
Can this Terraform-managed AWS infrastructure safely go to production?
```

It is intentionally reviewable. Teams can inspect the rule IDs, compare them
with internal cloud standards, and decide where environment-specific exceptions
belong.

## What This Pack Covers

- Database recovery: RDS backup retention, deletion protection, Multi-AZ
- Database exposure: public RDS access, private subnet posture, encryption
- Network posture: public security-group ingress, VPC endpoint private DNS
- Compute capacity: EC2 monitoring, autoscaling headroom, cloud quota headroom
- Identity posture: wildcard IAM, admin/owner access, broad AWS managed policies
- Object storage: public access, encryption, versioning, lifecycle, tags,
  recovery controls

## Example

```bash
python3 -m beacon.cli packs show terraform-aws-readiness
python3 -m beacon.cli packs rules terraform-aws-readiness
python3 -m beacon.cli readiness static examples/product-readiness/distributed-infra-risk --environment prod --no-html --no-open-report
```

## Relationship To Terraform/Sentinel/OPA

Sentinel and OPA are ideal for hard Terraform plan enforcement:

```text
Deny this plan if an RDS instance is publicly accessible.
```

Beacon uses this pack for release-readiness interpretation:

```text
Public ingress, weak database recovery controls, broad IAM, missing storage
recovery controls, and insufficient capacity headroom combine into a production
readiness concern.
```

