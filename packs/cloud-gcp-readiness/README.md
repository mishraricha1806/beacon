# GCP Cloud Readiness Pack

This pack defines the GCP checks Beacon currently supports for production
readiness.

It is intentionally honest about scope: the first preview covers Cloud SQL
network/backup/deletion-protection/HA posture, GCP firewall public ingress, GKE
private-node/control-plane access posture, Google Cloud Storage recovery/access
posture, and broad GCP project IAM grants. Quota and regional resiliency checks
are planned next.

## Current Coverage

- Cloud SQL public IP and authorized network posture
- Cloud SQL backup configuration posture
- Cloud SQL deletion protection posture
- Cloud SQL regional high-availability posture
- GCP firewall public ingress posture
- GKE private-node posture
- GKE master authorized network posture
- Google Cloud Storage bucket versioning posture
- Google Cloud Storage uniform bucket-level access posture
- Google Cloud Storage missing labels
- GCP project IAM `Owner`, `Editor`, and broad admin role blast-radius risk

## Planned Expansion

- Cloud SQL customer-managed encryption posture
- GKE regional workload resiliency posture
- deeper VPC private connectivity posture
- project quota and regional resiliency posture

## Commands

```bash
python3 -m beacon.cli packs show cloud-gcp-readiness
python3 -m beacon.cli packs rules cloud-gcp-readiness
```
