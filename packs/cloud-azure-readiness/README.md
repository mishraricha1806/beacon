# Azure Cloud Readiness Pack

This pack defines the Azure checks Beacon currently supports for production
readiness.

It is intentionally honest about scope: the first preview covers Azure managed
database network/backup/HA posture, Azure Key Vault public/purge posture,
private endpoint evidence for sensitive managed services, Azure Storage Account
posture, and broad Azure RBAC assignments. Quota and compute capacity checks
are planned next.

## Current Coverage

- Azure PostgreSQL/MySQL/MSSQL public network access posture
- Azure PostgreSQL/MySQL/MSSQL backup retention posture
- Azure PostgreSQL/MySQL/MSSQL high-availability posture
- Azure Key Vault public network access posture
- Azure Key Vault purge-protection posture
- Azure private endpoint evidence for managed databases and Key Vaults
- Azure Storage Account public blob access posture
- Azure Storage Account infrastructure encryption posture
- Azure Storage Account missing tags
- Azure RBAC `Owner`, `Contributor`, and `User Access Administrator` blast-radius risk

## Planned Expansion

- Azure managed database deletion protection and customer-managed encryption
  posture where supported by resource type
- Azure VM scale set and autoscaling headroom
- Azure subscription quota and regional resiliency posture

## Commands

```bash
python3 -m beacon.cli packs show cloud-azure-readiness
python3 -m beacon.cli packs rules cloud-azure-readiness
```
