# GCP Cloud Readiness Pack

This pack defines the GCP checks Beacon currently supports for production
readiness.

It is intentionally honest about scope: the first preview focuses on Google
Cloud Storage recovery/access posture and broad GCP project IAM grants. Cloud
SQL, GKE, VPC firewall, quota, and regional resiliency checks are planned next.

## Current Coverage

- Google Cloud Storage bucket versioning posture
- Google Cloud Storage uniform bucket-level access posture
- Google Cloud Storage missing labels
- GCP project IAM `Owner`, `Editor`, and broad admin role blast-radius risk

## Planned Expansion

- Cloud SQL backup, public exposure, deletion protection, encryption, and HA
  posture
- GKE and regional workload resiliency posture
- VPC firewall public ingress and private connectivity posture
- project quota and regional resiliency posture

## Commands

```bash
python3 -m beacon.cli packs show cloud-gcp-readiness
python3 -m beacon.cli packs rules cloud-gcp-readiness
```
