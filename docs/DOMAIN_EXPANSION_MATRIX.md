# Domain Expansion Matrix: Roadmap for Beacon

This document defines the scope, inputs, blocker rules, and MVP criteria for
expanding Beacon beyond the current Kafka-centric core into broader
infrastructure readiness.

## Current Domains (Stable GA)

These domains are production-ready and should remain the foundation:

1. **Static Config** (Terraform, Helm, Kubernetes YAML, Kafka config, CI/CD)
2. **Kafka Runtime** (cluster metadata, broker config, topics, consumer groups, ACLs, history)
3. **Kubernetes** (manifests and optional live workload diagnostics)
4. **Schema Registry** (compatibility, subject drift, compatibility mode)
5. **Prometheus/OpenTelemetry** (metrics collection and signal mapping)
6. **Runtime Snapshots** (flow, API, database, storage, deployment signals)

---

## Domain Tier: High ROI (Next 2 Domains — 30-90 Days)

These domains address the most cross-system incident patterns and have clear
blocker rules.

### Domain 1: API Gateway and Ingress Readiness

**Why** — Most enterprise services are exposed through API gateways (Kong, AWS
ALB, Nginx, Istio, Traefik). Gateway misconfig drives availability/latency
incidents downstream.

**Inputs**

- static config (Gateway YAML, route definitions, rate limit policies)
- live gateway metrics (request count, latency, error rate, queue depth)
- certificate chain and TLS version enforcement
- authentication provider and token validation rules
- dependent backend service list

**MVP Blocker Rules**

- `gateway.tls.version.unsupported` — TLS 1.0 or 1.1
- `gateway.auth.provider.unavailable` — auth service unreachable
- `gateway.rate_limit.disabled` — no rate limiting on public routes
- `gateway.backend.timeout.high` — timeout > 30s (indicates cascading dependency risk)
- `gateway.certificate.expiry.soon` — cert expiry <= 30 days
- `gateway.health_check.disabled` — health checks not configured on backends
- `gateway.response_buffer.unbounded` — no streaming limit on response size

**Additional Checks**

- timeout/retry budget consistency (prod should not retry all 5xx)
- circuit breaker state and recent trip count
- request queue depth vs capacity
- downstream service list matches deployment manifest

**Test Plan**

- test with simulated backend timeout (verify blocker)
- test with expired cert (verify blocker)
- test with disabled rate limit (verify blocker)
- test with auth provider fail (verify blocker)
- integration: run alongside current domains and verify no cross-domain blocker conflicts

---

### Domain 2: Database Readiness

**Why** — Database misconfig and degradation drive most P1 incidents in
microservice architectures. Connection pools, replication lag, backup freshness,
and migration safety are top blockers.

**Inputs**

- static config (connection pool size, query timeout, max connections,
  replication mode)
- live database metrics (open connections, lock wait time, replication lag,
  transaction rate)
- backup metadata (last backup time, retention, restore test results)
- migration scripts (schema migration safety checks)
- dependency graph (known consuming services)

**MVP Blocker Rules**

- `database.connection_pool.exhausted` — open connections >= max (immediate
  failure risk)
- `database.replication.lag.high` — replication lag > 10 seconds (failover risk)
- `database.backup.missing` — no recent backup (last backup > 24h)
- `database.backup.untested` — backup not verified in last 30 days
- `database.lock_contention.high` — lock wait time > 1 second
- `database.pool_size.inadequate` — pool_size < concurrent_clients estimate
- `database.query_timeout.missing` — no query timeout on long runners
- `database.max_connections.near_limit` — active connections > 80% of max
- `database.charset_collation.drift` — drift from prod charset (migration risk)

**Additional Checks**

- row count trends and growth rate
- slow query log / index efficiency
- ACID compliance mode and transaction isolation level
- encryption at rest and in transit
- user privilege assignment (least privilege check)

**Test Plan**

- test with simulated connection pool exhaustion (verify blocker)
- test with high replication lag (verify blocker)
- test with missing backup metadata (verify blocker)
- test with untested restore scenario (verify blocker)
- integration: run alongside Kafka + K8s and verify cross-domain logic works
  (e.g., high DB lag + high Kafka lag should trigger composite root-cause hypothesis)

---

## Domain Tier: Platform Core (Days 90-180)

These domains add platform-wide safety and should be implemented after the
high-ROI tier is stable.

### Domain 3: Service Mesh Readiness

**Why** — Service meshes (Istio, Linkerd, Consul) control resilience boundaries
(circuit breakers, retries, timeouts). Misconfig here amplifies cascading
failures.

**Inputs**

- service mesh config (retry policies, circuit breaker thresholds, timeout
  budgets per service pair)
- mesh metrics (request success rate, p99 latency, circuit breaker trip count)
- mutual TLS policy (permissive vs strict mode)
- VirtualService/DestinationRule definitions
- traffic policy (canary weight, traffic mirroring)

**MVP Blocker Rules**

- `mesh.mtls_policy.permissive` — mTLS not enforced (prod should be strict)
- `mesh.retry_budget.unbounded` — retries > 3 or no max concurrency
- `mesh.circuit_breaker.disabled` — no circuit breaker on unhealthy backend
- `mesh.timeout.missing` — no timeout on request route
- `mesh.timeout.excessive` — timeout > goal timeout (e.g., API SLA 2s but mesh timeout 30s)
- `mesh.traffic_policy.canary.stuck` — canary weight not advancing (indicates
  failure or manual halt)
- `mesh.tls_version.deprecated` — TLS 1.0/1.1 in mesh cert config

**Additional Checks**

- request rate limits per service pair
- load balancing algorithm vs traffic pattern (round robin for stateless OK;
  round robin for stateful is risk)
- outlier detection settings
- traffic shadowing configuration

**Test Plan**

- test with permissive mTLS (verify blocker)
- test with unbounded retry (verify blocker)
- test with disabled circuit breaker (verify blocker)
- test with missing timeout (verify blocker)
- integration: run alongside gateway/database and verify mesh-to-gateway
  timeout consistency rules work

---

### Domain 4: Cloud Capacity and Quota

**Why** — Cloud quota exhaustion and regional capacity limits cause hard
failures and are often missed in readiness gates.

**Inputs**

- cloud provider quota API (EC2 instances, S3 buckets, RDS slots, Kinesis
  shards, DynamoDB capacity)
- current usage metrics (by region, by resource type)
- growth forecast (trend analysis from last 30/60/90 days)
- planned infrastructure changes (Terraform plan)

**MVP Blocker Rules**

- `cloud.quota.exhausted` — usage >= soft/hard limit for any critical resource
- `cloud.quota.projected_exhaustion.critical` — given growth trend, quota
  exhausted within 14 days
- `cloud.quota_request.pending` — quota increase requested but not approved
- `cloud.region.capacity.unavailable` — target region out of capacity for
  instance type / AZ
- `cloud.nat_gateway.limit.near` — NAT gateways at 80% of limit

**Additional Checks**

- regional spread (single-region deployment is a blocker in prod)
- reserved capacity vs on-demand (cost and availability optimization)
- auto-scaling group limits vs max instances

**Test Plan**

- test with simulated quota exhaustion (verify blocker)
- test with growth forecast exceeding limit within SLA window (verify blocker)
- test with pending quota request (verify warning)
- integration: run alongside K8s and verify correlation (K8s node count +
  EC2 quota)

---

## Domain Tier: Resiliency and Governance (Day 180+)

These domains support compliance, DR validation, and policy-driven release
gating.

### Domain 5: Disaster Recovery Readiness

**Why** — DR readiness is rarely validated until incidents. RTO/RPO evidence
should be part of pre-deploy and pre-year-end readiness.

**Inputs**

- static DR policy (declared RTO, RPO)
- backup metadata and restore test results
- failover runbook and last-executed date
- data replication lag and cross-region setup
- DNS failover configuration and TTL
- incident recovery history

**MVP Blocker Rules** (for prod)

- `dr.rto_defined.missing` — no declared RTO
- `dr.rpo_defined.missing` — no declared RPO
- `dr.backup_restore_untested` — backup restore not tested within 90 days
- `dr.replication.lag.high` — data replication lag > RPO threshold
- `dr.failover_runbook.missing` — no documented failover procedure
- `dr.failover.last_executed.old` — last failover drill > 180 days ago
- `dr.dns_failover.ttl.high` — DNS TTL > RTO / 2 (recovery too slow)
- `dr.single_region.production` — prod deployed in only one region

**Additional Checks**

- failover endpoint health and routing configuration
- data consistency validation frequency
- blast radius of failover (dependent services impact)

**Test Plan**

- test with untested restore (verify blocker)
- test with high replication lag vs declared RPO (verify blocker)
- test with missing failover runbook (verify blocker)
- test with DNS TTL misaligned to RTO (verify blocker)

---

### Domain 6: Compliance and Policy Readiness

**Why** — Regulated environments (finance, healthcare, telecom) require
environment-specific proof of control. Beacon should emit compliance-scoped
findings.

**Inputs**

- organization and environment tier (dev, test, staging, prod)
- compliance standards (SOC2, PCI, HIPAA, GDPR)
- policy definitions (max TLS age, enforced encryption, audit logging,
  vendor approval list)
- audit log configuration and retention
- encryption at rest / in transit proof
- vendor/supplier SLO agreements

**MVP Blocker Rules** (per standard, per environment)

- `compliance.encryption_at_rest.missing` — no encryption for sensitive data
- `compliance.encryption_tls_version.unsupported` — TLS version below threshold
- `compliance.audit_logging.disabled` — audit logging not enabled
- `compliance.audit_log_retention.insufficient` — retention < required duration
- `compliance.vendor_approved.false` — dependency not on approved vendors list
- `compliance.mfa.not_enforced` — MFA not required for prod access
- `compliance.data_residency_violation` — data stored outside allowed region
- `compliance.backup_encrypted.false` — backups not encrypted

**Additional Checks**

- evidence of last audit review
- remediation tracking for known findings
- SLA breach history for third-party services

**Test Plan**

- test with encryption disabled (verify blocker)
- test with TLS version mismatch (verify blocker)
- test with audit logging disabled (verify blocker)
- test with vendor not on approved list (verify blocker)

---

## Domain 7: Incident History and Learning (Optional, High Value)

**Why** — enterprises often repeat incidents. If Beacon tracks postmortem
evidence + incident patterns, it can warn before similar failures recur.

**Inputs**

- incident postmortem data (incident date, root cause, affected services,
  duration)
- service dependency graph
- historical readiness scores before incident
- remediation status (fixed vs accepted risk)

**MVP Rules**

- `incident.similar_pattern.detected` — current readiness matches pre-incident
  signature
- `incident.remediation.incomplete` — known root cause not fixed
- `incident.remediation.sla_breach` — remediation SLA exceeded

**Test Plan**

- feed incident postmortem + current readiness and verify detection logic
- test with completed remediation (verify no blocker)
- test with SLA breach (verify escalation)

---

## Implementation Sequence

### Sequence Option A: Fast Enterprise Adoption (Recommended for most)

1. **Weeks 1-4:** API Gateway domain (highest frequency incident type)
2. **Weeks 5-8:** Database domain (highest blast radius)
3. **Weeks 9-16:** Service Mesh domain (enables cascading failure prevention)
4. **Weeks 17-20:** Cloud Quota domain (prevents hard failures)
5. **Long-term:** DR, Compliance, Incident Learning (as governance matures)

### Sequence Option B: Compliance-First (For regulated orgs)

1. **Weeks 1-4:** Compliance and Policy Readiness
2. **Weeks 5-8:** DR Readiness
3. **Weeks 9-12:** API Gateway
4. **Weeks 13-16:** Database
5. **Remaining:** Service Mesh, Cloud Quota, Incident Learning

### Sequence Option C: Platform-Centric (For k8s-heavy orgs)

1. **Weeks 1-4:** Service Mesh Readiness
2. **Weeks 5-8:** Cloud Quota and platform capacity
3. **Weeks 9-12:** Database domain
4. **Weeks 13-16:** API Gateway
5. **Remaining:** DR, Compliance, Incident Learning

---

## Validation Criteria for Each Domain

Before marking a domain ready for GA:

- [ ] at least 5 real-world blocker rules with high signal/low false-positive
- [ ] integration test suite (MVP checks + cross-domain correlation)
- [ ] input schema validation and clear error messages
- [ ] CLI and UI support for new domain inputs
- [ ] documentation with worked examples
- [ ] policy template for common standards
- [ ] telemetry and observability (CLI/UI logs rule evaluations)
- [ ] one week of production testing in a partner team's deployment
- [ ] remediation runbook for top 3 most common blockers

---

## Cross-Domain Rules: Critical for Enterprise Value

Once multiple domains are live, add correlation rules:

- **API Gateway + Database:** If gateway timeout < database max connection
  time, blocker (timeout will fire before recovery).
- **Service Mesh + Kafka:** If mesh retry policy > Kafka rebalance timeout,
  blocker (will amplify rebalance storms).
- **Database + Backup:** If backup SLA > RPO, blocker (backup too infrequent).
- **K8s + Cloud Quota + API Gateway:** If desired replica count × pod resource
  > available cloud quota, blocker.
- **Compliance + Encryption:** If standard requires encryption but auth uses
  bearer token without TLS, blocker.

---

## Success Metrics by Domain

### API Gateway Domain

- mean time to detect gateway-induced latency spike
- reduction in "downstream service unreachable" incidents
- percentage of certificate expiry alerts caught pre-crisis

### Database Domain

- reduction in connection pool exhaustion incidents
- improved RTO on failover (via replication lag monitoring)
- percentage of query timeouts prevented by early pool pressure detection

### Service Mesh Domain

- reduction in cascading failures (circuit breaker prevents secondary outages)
- improved canary promotion confidence (via traffic policy validation)
- mean time to detect mTLS policy drift

### Cloud Quota Domain

- prevention of "quota exceeded" hard failures
- lead time improvement on quota requests (caught 14 days early instead of at
  failure)

### DR Readiness Domain

- restore success rate improvement (via untested restore detection)
- mean time to recover improvement (via RTO validation)

### Compliance Domain

- audit finding resolution time
- policy drift detection latency
- vendor SLO breach prevention

---

## Recommended Quick Wins (Immediate)

If you want quick wins while planning the full expansion:

1. Add **logging connector** (CloudWatch, DataDog, Splunk API) to collect audit
   logs and security events as evidence.
2. Add **certificate expiry checker** (across Kafka, API gateway, databases,
   registries).
3. Add **DNS resolution validator** (bootstrap servers, database hosts, schema
   registry, API gateways resolve correctly).
4. Add **network latency profiler** (collect round-trip times to key services
   and flag high-latency paths).

These four additions would increase confidence in the current domains without
requiring new domain logic.

---

## Backlog for Future Expansion (Year 2+)

- **Cache Readiness** (Redis, Memcached eviction policy, connection limits)
- **Message Queue Readiness** (RabbitMQ, SQS, AWS SNS queue depth, DLQ
  backlog)
- **CDN Readiness** (cache hit rates, origin latency, certificate validity)
- **Observability Readiness** (trace sampling, log cardinality, retention
  policy)
- **Supply Chain Readiness** (dependency vulnerability scanning, license
  compliance)
- **Change Management** (change frequency vs incident rate correlation,
  MTTR by change type)


