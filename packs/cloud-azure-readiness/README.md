# Azure Cloud Readiness Pack

This pack defines the Azure checks Beacon currently supports for production
readiness.

It is intentionally honest about scope: the first preview focuses on Azure
Storage Account posture and broad Azure RBAC assignments. Azure managed
database, Key Vault, private endpoint, quota, and compute capacity checks are
planned next.

## Current Coverage

- Azure Storage Account public blob access posture
- Azure Storage Account infrastructure encryption posture
- Azure Storage Account missing tags
- Azure RBAC `Owner`, `Contributor`, and `User Access Administrator` blast-radius risk

## Planned Expansion

- Azure SQL, PostgreSQL, and MySQL backup, public exposure, deletion protection,
  encryption, and HA posture
- Azure VM scale set and autoscaling headroom
- Azure Key Vault and private endpoint posture
- Azure subscription quota and regional resiliency posture

## Commands

```bash
python3 -m beacon.cli packs show cloud-azure-readiness
python3 -m beacon.cli packs rules cloud-azure-readiness
```
