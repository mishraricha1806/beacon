# Readiness Use-Case Review (Current Coverage + Gaps)

Date: 2026-06-08
Review scope: readiness-oriented paths across rules, metadata, CLI, and tests

## Review Method

This review was based on:

- registered rule sources under `beacon/rules/*.py`
- rule metadata under `beacon/rules/metadata/*.yaml`
- readiness command surface in `beacon/cli.py`
- release contract tests in `tests/test_module1_release_contract.py`

## Findings (Prioritized)

### High 1: Kubernetes readiness depth is still minimal for enterprise gating

Evidence:

- `beacon/rules/kubernetes_registered_rules.py` currently registers 5 core rules:
  replicas, resources, probes, privileged container, mutable image tag.

Impact:

- good baseline but insufficient for stricter enterprise readiness standards.
- missing many common pre-deploy controls (policy, security context, networking,
  disruption and deployment safety).

Recommendation:

- add a Phase-1 Kubernetes readiness pack (listed in Gaps section).

### High 2: Cloud readiness coverage is AWS-heavy and narrow

Evidence:

- `beacon/rules/cloud_registered_rules.py` contains 4 rules focused on
  security group ingress, RDS exposure/backup, EC2 monitoring.
- storage rules add cross-cloud checks, but broader cloud readiness controls
  are not yet present.

Impact:

- multi-cloud enterprise teams will see partial readiness confidence.

Recommendation:

- add quota/capacity, HA/regional resilience, logging, key-management,
  and provider-balanced controls.

### Medium 3: IAM readiness rules depend on raw string matching

Evidence:

- `beacon/rules/iam_registered_rules.py` checks wildcard/admin patterns using
  simple substring matching in raw policy text.

Impact:

- may produce false positives/negatives for formatting variants and policy docs.

Recommendation:

- parse structured IAM policies (JSON document semantics) and evaluate actions,
  resources, conditions, and effect fields explicitly.

### Medium 4: CI/CD readiness guardrails are limited to a few GitHub workflow checks

Evidence:

- `beacon/rules/cicd_registered_rules.py` defines 3 rules:
  protected environment missing, `pull_request_target`, `write-all` permissions.

Impact:

- key supply-chain and deployment-governance checks are still missing.

Recommendation:

- expand with pinning, provenance, branch protection, environment secrets usage,
  and deployment freeze-window controls.

## Current Readiness Use Cases Already Implemented

### Newly Added in the Enterprise Readiness Expansion

The latest readiness expansion added these concrete use cases:

- Kubernetes hardening: `runAsNonRoot`, `allowPrivilegeEscalation`,
  `readOnlyRootFilesystem`, `seccompProfile`, and host namespace sharing
- Kubernetes disruption safety: topology spread / anti-affinity expectations and
  PodDisruptionBudget presence within the evaluated manifest set
- Kubernetes east-west isolation: matching NetworkPolicy presence within the
  evaluated manifest set
- Cloud quota readiness: declared quota profile headroom checks
- Cloud HA posture: single-region production detection and RDS Multi-AZ checks
- Cloud private access controls: explicit DB subnet placement and VPC endpoint
  private DNS checks
- CI/CD supply-chain controls: third-party action SHA pinning, deployment job
  timeout, and concurrency governance
- IAM structured evaluation: AWS policy statement parsing plus structured GCP /
  Azure role pattern handling with backward-compatible fallback
- Cross-domain readiness correlations: exposed database path, public unencrypted
  storage, uncontrolled production deploy path, Kubernetes compounded
  single-point-of-failure, and quota-vs-autoscaling mismatch

## 1) Kafka Readiness (Strong)

Broad non-runtime Kafka coverage exists across:

- broker defaults and safety (`default replication`, `offset replication`,
  `unclean leader election`, `rack awareness`, `authorizer`, plaintext listeners)
- cluster posture (`under-replicated`, `offline partitions`, leader imbalance,
  topic-count pressure)
- topic guardrails (`replication factor`, `min ISR`, retention/compaction,
  segment sizing, schema compatibility, owner metadata)
- producer/consumer config checks (`acks`, idempotence, in-flight requests,
  auto-commit/reset, DLQ, concurrency)
- offline ACL/history inputs for trend and posture checks

Reference signal:

- metadata includes a large Kafka readiness set (non-runtime and runtime-aware
  paths are both present).

## 2) Kubernetes Manifest Readiness (Baseline)

Implemented static checks:

- single-replica workload risk
- missing requests/limits
- missing readiness/liveness probes
- privileged container
- mutable image tag (`latest` or unpinned)

## 3) Object Storage Readiness (Good baseline)

Implemented static checks:

- public access exposure
- encryption missing
- versioning missing
- lifecycle policy missing
- tags/labels missing
- GCP uniform bucket-level access disabled

## 4) Cloud Infrastructure Readiness (Initial)

Implemented static checks:

- AWS security group open ingress
- AWS RDS publicly accessible
- AWS RDS backup retention missing
- AWS EC2 detailed monitoring disabled

## 5) IAM Readiness (Initial)

Implemented static checks:

- wildcard permissions
- owner/admin excessive access

## 6) CI/CD Readiness (Initial)

Implemented static checks:

- deploy-like job missing protected environment
- risky `pull_request_target` trigger
- `write-all` token permissions

## 7) Topology Readiness (Initial)

Implemented static checks:

- high blast radius service
- critical service single instance
- missing service owner

## 8) Schema Registry Readiness (Config + collector path)

Implemented checks include:

- URL missing / query failure handling
- global/subject compatibility unsafe
- missing expected topic subjects
- schema metadata visibility gaps

## Readiness Use Cases Still Missing (Recommended Backlog)

## A) Kubernetes Readiness Gaps

1. unsafe Linux capabilities not dropped
2. image digest pinning missing
3. service account token automount uncontrolled
4. HPA absent for autoscaled services
5. namespace-level default deny posture checks across manifest sets

## B) Kafka Readiness Gaps (remaining high-value)

1. listener/TLS cipher policy compliance matrix by environment
2. ISR/replication constraints tied to environment profile explicitly
3. topic-level naming/ownership conventions (governance pack)
4. quota policy checks for producer/consumer isolation standards
5. retention policy consistency against declared RPO/RTO profile
6. DR-specific cluster-level readiness checks (cross-region mirror posture)

## C) Cloud Readiness Gaps

1. KMS key rotation and policy guardrails
2. log/audit trail controls by environment
3. security group egress governance
4. managed service backup restore policy presence checks
5. provider parity beyond the currently modeled AWS-first rules

## D) CI/CD Readiness Gaps

1. required reviewers / branch protection enforcement
2. artifact provenance/signing requirement checks
3. untrusted fork execution controls
4. deployment freeze window / change calendar integration
5. required security/readiness checks in workflow gates

## E) IAM Readiness Gaps

1. condition-aware least privilege evaluation
2. cross-account trust policy risk checks
3. role assumption chain constraints
4. stale principal/service-account ownership validation
5. policy exception and expiry metadata checks

## F) Topology and Ownership Gaps

1. dependency critical path without fallback detection
2. upstream/downstream timeout and retry budget alignment
3. runbook / escalation metadata presence checks
4. ownership mapping consistency with deployment manifests

## Suggested Stepwise Order (Readiness-Only)

1. Expand Kubernetes static readiness pack
2. Add cloud quota + regional HA readiness
3. Expand CI/CD governance and supply-chain readiness
4. Improve IAM parser from string matching to structured policy evaluation
5. Expand cross-domain readiness correlation rules with environment-specific
   policy thresholds and deployment-architecture evidence

## Implementation Acceptance Criteria

For each new domain pack:

- at least 5 high-signal deterministic rules
- environment-aware severity mapping
- example input fixtures under `examples/supported/`
- unit and integration tests under `tests/`
- rule metadata entries under `beacon/rules/metadata/`
- release contract extension where applicable

## Conclusion

The current readiness foundation is strong in Kafka and good in core static
infrastructure checks. For enterprise-grade environment readiness, the largest
remaining value is in deeper Kubernetes/cloud/CI/CD/IAM policy packs and
cross-domain deterministic correlations.

