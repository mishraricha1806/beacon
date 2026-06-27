# Beacon Readiness Packs

Readiness packs make Beacon's checks visible and discussable.

Beacon is still the runner, normalizer, scorer, reporter, and UI. Packs are the
inspectable rule groupings behind that experience. They let teams review which
signals are used, adapt them to local standards, and debate operational
judgement without treating Beacon as a black box.

## Available Packs

| Pack | Purpose |
| --- | --- |
| `kafka-production-readiness` | Kafka topic, broker, client, Schema Registry, ACL, runtime, and replay readiness checks. |
| `kubernetes-production-readiness` | Kubernetes workload, admission, RBAC, security, capacity, and runtime readiness checks. |
| `cloud-production-readiness` | Cross-cloud production-readiness posture for network, identity, database, object-storage, quota, and capacity risks. |
| `cloud-azure-readiness` | Azure Storage Account and RBAC readiness checks with planned Azure database, network, compute, and quota expansion. |
| `cloud-gcp-readiness` | GCP Cloud Storage and project IAM readiness checks with planned Cloud SQL, GKE, VPC, and quota expansion. |
| `terraform-aws-readiness` | Terraform-managed AWS database, network, IAM, object-storage, and capacity readiness checks. |
| `iac-coverage-readiness` | Unmanaged cloud resources outside Terraform state, ownership, activity, and disposition readiness checks. |
| `distributed-system-production-readiness` | Cross-domain production-readiness checks across Kafka, Kubernetes, cloud, IaC coverage, CI/CD, topology, and flow. |

## Commands

```bash
python3 -m beacon.cli packs list
python3 -m beacon.cli packs show kafka-production-readiness
python3 -m beacon.cli packs rules kafka-production-readiness
python3 -m beacon.cli packs show kubernetes-production-readiness
python3 -m beacon.cli packs rules kubernetes-production-readiness
python3 -m beacon.cli packs show cloud-production-readiness
python3 -m beacon.cli packs rules cloud-production-readiness
python3 -m beacon.cli packs show cloud-azure-readiness
python3 -m beacon.cli packs rules cloud-azure-readiness
python3 -m beacon.cli packs show cloud-gcp-readiness
python3 -m beacon.cli packs rules cloud-gcp-readiness
python3 -m beacon.cli packs show terraform-aws-readiness
python3 -m beacon.cli packs rules terraform-aws-readiness
python3 -m beacon.cli packs show iac-coverage-readiness
python3 -m beacon.cli packs rules iac-coverage-readiness
python3 -m beacon.cli packs show distributed-system-production-readiness
python3 -m beacon.cli packs rules distributed-system-production-readiness
```

## Why Packs?

OPA and Sentinel are strong policy-enforcement layers. Beacon packs are not a
replacement for that. They are a release-readiness layer:

- group related operational risks
- connect static config and runtime signals
- explain business impact
- rank what to fix first
- keep the underlying checks visible
