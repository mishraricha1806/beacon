# Beacon Enterprise Review, Code Findings, and Feature Roadmap

Date: 2026-06-08

## Executive Assessment

Beacon is useful for large enterprises today, especially as a deterministic
readiness gate for Kafka-centric and platform-heavy systems. The current design
already supports multi-domain evidence (static config, runtime snapshots, flow,
Prometheus, OpenTelemetry, Schema Registry, Kafka ACL/history, and deployment
events), which maps well to enterprise release governance.

To become a full-flex enterprise app, the largest gaps are around operational
hardening of the local UI path, stronger platform integrations, and scalable
multi-tenant execution patterns.

## Code Review Findings (Prioritized)

### 1) High: Unbounded multipart upload parsing can cause memory/DoS risk

**Where**

- `beacon/ui.py:1072`
- `beacon/ui.py:1090`

**What**

- `cgi.FieldStorage` parses request bodies without explicit request-size guard.
- uploaded file data is read fully into memory (`item.file.read()`) before being
  written to disk.

**Impact in enterprise**

- large or malicious uploads can spike memory and crash the process.
- risk is amplified if UI is exposed beyond localhost.

**Recommended update**

- enforce max request size and per-file size limits.
- stream uploads directly to a bounded temp file instead of whole-buffer read.
- return HTTP 413 for oversized payloads.

### 2) High: Uploaded sensitive artifacts are persisted without cleanup

**Where**

- `beacon/ui.py:1101`
- `beacon/ui.py:1110`
- `beacon/ui.py:1120` to `beacon/ui.py:1350`

**What**

- temp files are created with `delete=False` for certs, keys, configs.
- no request-scope cleanup deletes those files after processing.

**Impact in enterprise**

- credentials/certs can remain on disk.
- long-running UI sessions leak disk over time and expand data exposure.

**Recommended update**

- track all request-created temp files and delete them in a `finally` block.
- add a startup janitor for stale files matching `beacon-kafka-ui-*`.
- support optional encrypted temp storage location.

### 3) Medium: Deprecated `cgi` parser increases upgrade risk

**Where**

- `beacon/ui.py:1073`

**What**

- multipart handling uses Python `cgi.FieldStorage`, which is deprecated.

**Impact in enterprise**

- increases future Python upgrade friction and support risk.

**Recommended update**

- replace with a maintained multipart parser (or move UI to FastAPI/Starlette
  with tested upload handling and limits).

### 4) Medium: UI has no authn/authz guard if bound to non-local interface

**Where**

- `beacon/ui.py:992` to `beacon/ui.py:1022`
- `beacon/ui.py:1646`

**What**

- UI accepts POST requests without authentication checks.
- host is configurable; accidental `0.0.0.0` exposure is possible.

**Impact in enterprise**

- unauthorized users could submit workloads or exfiltrate analysis artifacts.

**Recommended update**

- keep localhost default, and add optional auth middleware/token.
- add explicit safety warning when host is non-local.
- provide reverse-proxy reference (OIDC/SSO) for enterprise deployment.

### 5) Medium: Kafka metadata timeout is fixed and may cause false failures

**Where**

- `beacon/kafka_runtime_connector.py:264`
- `beacon/kafka_runtime_connector.py:72`

**What**

- `list_topics(timeout=3)` is hardcoded and can fail in high-latency or
  heavily loaded enterprise environments.

**Impact in enterprise**

- intermittent false negatives (`_TRANSPORT` / timeout-like connection failures)
  during transient network conditions.

**Recommended update**

- expose metadata timeout/retry/backoff through CLI/UI/config.
- add first-failure retry with jitter and classify timeout vs auth vs DNS.

## Why Beacon Is Enterprise-Useful

Beacon aligns with common enterprise control needs:

- deterministic release governance (repeatable readiness decisions)
- cross-domain evidence correlation instead of siloed metrics
- policy overlay support for environment-specific strictness
- read-only diagnostics model (safer operational posture)
- JSON outputs suitable for CI/CD gates and audit trails

## Additional Enterprise Use Cases to Add

1. **Release Gate as a Service**
   - centralized API that receives evidence bundles and returns signed decisions.
2. **Multi-Cluster Fleet Readiness**
   - run readiness across all Kafka/Kubernetes clusters and rank systemic risk.
3. **Pre-Change Risk Simulation**
   - compare planned infra diff against historical incident signatures.
4. **DR Readiness and Failover Certification**
   - verify RTO/RPO and replay survivability before DR drills.
5. **Regulated Environment Evidence Pack**
   - export immutable audit bundle for compliance sign-off.
6. **Supplier/Dependency Readiness Lens**
   - include external dependency SLO signals in release decisions.
7. **Golden Path Scorecards**
   - benchmark teams/apps against platform baseline and trend debt burn-down.
8. **Multi-Tenant Policy Governance**
   - global baseline policy + BU/tenant overlays with expiry-based waivers.
9. **Incident Replay and Learning**
   - feed postmortem evidence to compare future incidents against known patterns.
10. **Executive Readiness Dashboard**
   - environment readiness trend, top blockers, SLA to remediation.

## Feature Roadmap to Become a Full-Flex App

### Phase 1: Hardening (0-30 days)

- request/file size limits in UI upload path
- secure temp file lifecycle and cleanup
- configurable Kafka metadata timeout + retries
- improved connection failure taxonomy (DNS/TLS/auth/network)
- auth guard for non-local UI deployments

### Phase 2: Platformization (30-90 days)

- service mode (REST API) with job queue and async execution
- SSO/OIDC, RBAC, tenant isolation, and audit logs
- pluggable evidence connectors (cloud APIs, CI systems, ticketing)
- centralized policy registry and signed policy versions
- persistent findings store + trend analytics

### Phase 3: Enterprise Scale (90+ days)

- distributed execution for large fleets
- change-intelligence model (pre/post comparison and drift impact)
- recommendation engine with remediation runbooks
- approval workflow integration (ServiceNow/Jira/GitHub)
- SLA-driven risk exceptions with auto-expiry and escalation

## Recommended Non-Functional Requirements

- Availability target for API mode (for example, 99.9%)
- P95 analysis latency SLO per evidence bundle size tier
- strict secret handling (encryption in transit/at rest)
- tenant data isolation and retention controls
- full decision traceability (who/what/when/policy version/evidence hash)

## Testing Updates Recommended

Add tests for the identified risk areas:

- multipart oversize request rejected with 413
- uploaded temp files removed on success and on exception
- non-local host requires explicit auth mode or hard warning
- configurable Kafka timeout/retry path under simulated latency
- integration test for multi-source `readiness all` gating behavior

## Suggested Success Metrics

- false-positive blocker rate by environment
- mean time to identify top likely cause in diagnostics
- percentage of releases passing first-attempt readiness gate
- blocker remediation lead time
- number of incidents prevented by pre-release findings

## Conclusion

Beacon already provides strong enterprise value where deterministic readiness and
runtime evidence correlation are critical. The next leap to a full-flex
enterprise platform is primarily operational hardening + platform deployment
capabilities, not a rewrite of core rule logic.

