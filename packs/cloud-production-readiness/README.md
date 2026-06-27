# Cloud Production Readiness Pack

This pack is the cloud-facing readiness pack Beacon should present publicly.
It answers:

```text
Can this cloud-managed infrastructure safely go to production?
```

The current implementation is strongest for AWS-backed Terraform and cloud
inventory signals, but the pack is intentionally named around the cross-cloud
readiness concept: network exposure, identity blast radius, object-storage
recovery, managed database survivability, and capacity headroom.

## Current Coverage

- AWS-backed Terraform and cloud inventory signals
- Azure managed database, storage, and RBAC readiness signals
- GCP Cloud SQL, Cloud Storage, and IAM readiness signals
- object-storage public access, encryption, versioning, lifecycle, and recovery
- identity wildcard/admin blast-radius checks
- managed database exposure, backup, deletion protection, encryption, and HA
- cloud network exposure and private connectivity posture
- quota and autoscaling capacity headroom

## Planned Provider Expansion

- deeper Azure compute, quota, and regional resiliency readiness
- deeper GCP quota, regional workload, and private connectivity readiness
- provider-specific evidence mapping for equivalent controls

## Commands

```bash
python3 -m beacon.cli packs show cloud-production-readiness
python3 -m beacon.cli packs rules cloud-production-readiness
```

## Important Scope Note

This pack does not claim full AWS, Azure, and GCP parity yet. It gives Beacon a
cloud-neutral product surface while keeping provider-specific evidence honest.
Use `terraform-aws-readiness` when you want to inspect the current AWS-focused
provider pack directly.
