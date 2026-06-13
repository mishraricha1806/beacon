# Beacon Environment Readiness Focus: Scope Refinement

Date: 2026-06-08

## Clarification: Readiness vs Operations

**Readiness Mode (Pre-Deploy, Static)**
- "Is this environment safe to deploy to right now?"
- focuses on configuration, policy compliance, resource guardrails, and capacity
- deterministic (no live metrics, no incident diagnosis)
- gate: pass/block decision before rollout

**Operations Mode (Post-Deploy, Live)**
- "Why is this running system degrading?"
- focuses on live metrics, incident diagnosis, runtime correlation
- probabilistic (evidence-based root-cause hypotheses)
- context: troubleshooting active issues

---

## Current Beacon Domains: Readiness vs Operations Split

### Readiness-Aligned Domains (Keep/Expand)

1. **Static Config** ✓ readiness
   - infrastructure as code (Terraform, Helm, Kubernetes YAML)
   - CI/CD workflow definitions
   - policy compliance rules
2. **Kafka Config Readiness** ✓ readiness
   - topic replication factor, retention, compaction settings
   - broker configuration safety
   - schema registry compatibility mode
3. **Kubernetes Manifest Readiness** ✓ readiness
   - resource requests/limits
   - security policies (RBAC, network policies, pod security standards)
   - deployment strategy (rolling update guards, health checks)

### Operations-Aligned Domains (Skip/Reduce)

4. **Kafka Runtime** ✗ operational
   - live consumer group lag
   - broker metrics and disk usage
   - rebalance signals

5. **Kubernetes Live** ✗ operational
   - pod restart counts, node pressure
   - active workload churn

6. **Runtime Snapshots** ⚠ hybrid (can be readiness if pre-deploy, operational if post-deploy)
   - latency trends, error rates, deployment correlation

---

## Recommended Environment Readiness Domains (Focused Roadmap)

Keep Beacon as a **pre-deploy deterministic gate** by adding these readiness
domains:

### Tier 1: High-ROI Readiness (Next 30-60 Days)

#### 1. API Gateway / Ingress Configuration Readiness

**What it checks** (static, not live)
- certificate validity and chain correctness
- TLS version enforcement (min 1.2 or 1.3)
- authentication provider configuration and attribute mapping
- rate limit policy enforcement (must exist on public routes)
- request/response size guardails
- timeout configuration alignment with downstream SLAs
- health check configuration on backends
- CORS policy strictness

**Example blockers**
- `gateway.certificate.expired` — certificate already expired
- `gateway.certificate.expiry.too_soon` — expiry within 14 days
- `gateway.tls.version.deprecated` — TLS 1.0 or 1.1 configured
- `gateway.authentication.missing` — public route has no auth policy
- `gateway.rate_limit.missing` — public endpoint not rate limited
- `gateway.timeout.missing` — no timeout defined (can hang forever)
- `gateway.cors.overly_permissive` — allows any origin on sensitive endpoint

**Inputs**
- Gateway YAML config (Kong, Nginx Ingress, AWS ALB, Istio VirtualService)
- Certificate files (for embedded cert validation)
- Route-to-backend mapping (to validate SLA alignment)

**Why readiness not operations**
- these checks run on config before deployment
- no live traffic needed
- deterministic pass/fail

---

#### 2. Database Configuration Readiness

**What it checks** (static, not live)
- connection pool sizing vs expected concurrent clients estimate
- query timeout configuration
- backup procedure definition and retention policy
- encryption at rest and in transit (config-based)
- max connections and resource limits vs instance type
- replication configuration (sync vs async) and standby setup
- parameter group settings (slow query log, audit logging)
- character set and collation consistency with schema
- user permission least-privilege correctness

**Example blockers**
- `database.backup_procedure.missing` — no automated backup defined
- `database.backup_retention.insufficient` — retention < 7 days
- `database.encryption_at_rest.disabled` — encryption not enabled
- `database.encryption_tls.disabled` — plaintext connections allowed
- `database.pool_size.too_small` — pool size < estimated concurrent (based on deployment)
- `database.query_timeout.missing` — no timeout on long-running queries
- `database.replication.standby_missing` — no standby database for failover
- `database.user_permissions.overly_broad` — non-app users have write access

**Inputs**
- Database configuration file (RDS parameter group, CloudSQL flags, Postgres config)
- Database schema (to infer write patterns)
- Deployment manifest (to estimate concurrent connections: replicas × DB client threads)
- Backup policy (to validate retention)

**Why readiness not operations**
- these checks run on config/schema before deployment
- no live performance metrics needed
- deterministic pass/fail

---

#### 3. Cloud Governance and Quota Readiness

**What it checks** (static + quota API)
- cloud quota vs planned resource request
- projected quota exhaustion based on growth trend (optional historical data)
- regional deployment spread (no single-region prod)
- cost allocation tags and billing guardrails
- auto-scaling group limits vs requested capacity
- resource naming convention compliance
- cross-region replication setup for critical resources

**Example blockers**
- `cloud.quota.insufficient` — requested instances exceed available quota
- `cloud.quota.projected_exhaustion` — growth forecast exhausts quota within 90 days
- `cloud.single_region.production` — prod deployed in only one region (no HA)
- `cloud.cost_tags.missing` — resource lacks required cost allocation tags
- `cloud.autoscaling.limit.inadequate` — max instances < peak projected load

**Inputs**
- cloud provider quota snapshot (EC2 vCPU, RDS instances, Kinesis shards, etc.)
- terraform/helm plan (to see requested resource counts)
- growth trend data (last 30/60/90 days usage)
- cost allocation configs

**Why readiness not operations**
- these checks run pre-deployment to catch quota blockers early
- no live metrics or scaling events needed
- deterministic pass/fail

---

#### 4. Security and Compliance Configuration Readiness

**What it checks** (static, not live)
- encryption enforcement (data at rest, in transit, backups)
- secret management (no secrets in repo, no plaintext credentials in config)
- RBAC policy definition (least privilege roles defined)
- network policy / security group rules (default deny, explicit allow)
- audit logging configuration
- certificate and SSH key rotation policy
- compliance-specific controls (HIPAA, SOC2, PCI, GDPR)

**Example blockers**
- `security.secret.hardcoded` — API key/password found in code or config
- `security.encryption_at_rest.missing` — sensitive data not encrypted
- `security.rbac.overly_permissive` — wildcard permissions on sensitive resources
- `security.network_policy.missing` — pod/VM has no ingress restrictions
- `security.audit_logging.disabled` — audit logging not enabled
- `security.tls_certificate.untrusted` — self-signed cert in prod
- `security.ssh_key.shared` — shared SSH key instead of individual keys
- `compliance.gdpr.data_residency_violation` — EU data stored outside EU

**Inputs**
- Infrastructure config (Terraform, Kubernetes YAML, IaC)
- Application config (environment variables, ConfigMaps, Secrets)
- Git repo commit history (to detect secrets added)
- policy definitions (RBAC roles, network policies)

**Why readiness not operations**
- these checks run on configuration
- no live access logs or attack telemetry needed
- deterministic pass/fail

---

#### 5. Infrastructure as Code Quality and Conventions

**What it checks** (static)
- naming convention compliance (matches org standards)
- documentation completeness (comments, terraform modules documented)
- variable and secret exfiltration safety (no hardcoded secrets)
- consistency across environments (dev/test/staging/prod use same base template)
- module reuse (discourage one-off configs)
- GitOps hygiene (who can merge, approval requirements, branch protection)
- infrastructure versioning (track config changes and rollback capability)

**Example blockers**
- `iac.naming_convention.violated` — resource name doesn't match pattern
- `iac.documentation.insufficient` — module lacks description
- `iac.secret.hardcoded` — secret string in IaC
- `iac.environment_consistency.drift` — prod config differs from template in undocumented way
- `iac.version_control.missing` — config not tracked or too old
- `iac.review_policy.missing` — no human approval before production merge

**Inputs**
- Terraform/CloudFormation code
- Helm values and templates
- Kubernetes manifests
- CI/CD pipeline config
- Git repo policies (branch protection, approvers)

**Why readiness not operations**
- these checks run on source code/configuration
- no deployment or live execution needed
- deterministic pass/fail

---

### Tier 2: Compliance and Policy Readiness (60-120 Days)

#### 6. Regulatory Compliance Framework

**What it checks** (static + policy mapping)
- encryption standards (algorithm, key length)
- audit trail requirements (event logging, retention)
- data residency constraints (region/country)
- vendor approval and SLO agreements
- PII handling and minimization
- access control logging and segregation of duties
- change management process compliance

**Example blockers** (per environment × standard)
- `compliance.sox.change_approval.missing` — change SLO changes not approved
- `compliance.hipaa.encryption.insufficient` — algorithm weaker than required
- `compliance.pci.audit_retention.insufficient` — logs retained < required
- `compliance.gdpr.data_deletion.unimplemented` — no deletion capability for user data
- `compliance.hipaa.access_logging.disabled` — PHI access not logged
- `compliance.pci.vendor_approved.false` — pay processor not on approved list

**Inputs**
- compliance standards document (internal policy)
- infrastructure configuration (encryption alg, logging config, access controls)
- vendor agreements and SLAs
- infrastructure audit trail

**Why readiness not operations**
- these checks run on configuration
- no live compliance audit data needed
- deterministic pass/fail

---

#### 7. Environment Policy Enforcement

**What it checks** (static, policy-based)
- environment-specific strictness (dev vs prod)
- cost optimization guardrails (instance sizing, autoscaling)
- capacity planning accuracy (peak load estimate vs instance count)
- dependency version pins (no open-ended version constraints in prod)
- deployment strategy governance (blue/green, canary, rolling)
- resource reservation vs bursting vs on-demand mix

**Example blockers** (per environment)
- `policy.prod.encryption.required` — encryption disabled in prod
- `policy.prod.backup.required` — backup not configured in prod
- `policy.prod.cost.oversized` — instance oversized, optimize or use reserved
- `policy.staging.approval_count.insufficient` — < required reviewers
- `policy.dev.cost_constraints.violated` — resource usage exceeds dev budget

**Inputs**
- infrastructure configuration
- environment tag or policy assignment
- deployment strategy definition
- policy registry (organization-defined rules)

**Why readiness not operations**
- these checks run on configuration and policy
- no live enforcement data needed
- deterministic pass/fail

---

## What to Skip (Operational, Not Readiness)

Do **not** add these as environment readiness domains:

- live Kafka consumer lag
- live pod restart counts or node pressure
- runtime API latency or error rates
- deployment correlation with live incident windows
- live backup restore testing
- live circuit breaker trip counts
- live DNS resolution times

These are **operational diagnostics** (good for post-deploy troubleshooting) but
not **readiness** (pre-deploy gates).

---

## Recommended Implementation Sequence (Readiness-Only)

### Phase 1: Foundation (Weeks 1-6)

1. **API Gateway Config Readiness** — highest frequency gating logic
2. **Database Config Readiness** — highest blast radius

### Phase 2: Governance (Weeks 7-12)

3. **Cloud Quota Readiness**
4. **Security + Compliance Config Readiness**

### Phase 3: Organizational Scale (Weeks 13+)

5. **IaC Quality and Conventions**
6. **Regulatory Compliance Framework**
7. **Environment Policy Enforcement**

---

## Key Success Criteria for Environment Readiness

An environment is **ready** when:

- [ ] no unresolved blocking findings for that environment profile
- [ ] all critical configuration guardrails met (encryption, auth, backups)
- [ ] quota sufficient for planned resource request
- [ ] policy exceptions documented and approved with expiry dates
- [ ] compliance controls verified against policy baseline
- [ ] deployment strategy safe for the target environment (prod = rolling+healthcheck)
- [ ] security posture meets minimum standard (no hardcoded secrets, RBAC in place)

---

## What Stays Operational (Current Kafka/K8s/Runtime)

Keep these domains as **diagnostic/observational** (post-deploy, optional enrichment):

- Kafka runtime insights (consumer lag, broker state) — for incident investigation only
- Kubernetes runtime insights (pod health, node pressure) — for post-deploy validation only
- runtime snapshots (API latency trends) — optional enrichment, not blocking gate

These **do not** block promotion; they enriched post-deploy diagnostics.

---

## Summary: Environment Readiness Domains for Beacon

**Tier 1 (Immediate, High ROI)**
1. API Gateway Configuration Readiness
2. Database Configuration Readiness

**Tier 2 (Next 30-60 Days)**
3. Cloud Governance and Quota Readiness
4. Security and Compliance Configuration Readiness

**Tier 3 (60-120 Days)**
5. Infrastructure as Code Quality
6. Regulatory Compliance Framework
7. Environment Policy Enforcement

All of these are **deterministic, configuration-based, pre-deployment gates** —
exactly what enterprise readiness requires.

No operational/runtime metrics or incident diagnostics included.

