# Shared Control Plane Entry Criteria

Beacon's shared control plane is intentionally deferred. The current UI is a
local operator interface without authentication, authorization, or tenant
isolation and must not be exposed as an organizational service.

## Pilot exit criteria

Control-plane implementation may begin only after at least three service teams
complete a four- to six-week CLI pilot and demonstrate:

- acceptable onboarding time, runtime, false-positive rate, and evidence freshness;
- named ownership for blocking rules and waivers;
- stable report, release-evidence, and readiness-pack contracts;
- immutable distribution and green security/supply-chain gates;
- repeatable release decisions that improve outcomes rather than a vanity score.

## Required architecture before shared deployment

The design review must cover:

- SSO/OIDC, role-based authorization, tenant isolation, and least privilege;
- envelope encryption, managed secrets, key rotation, and data classification;
- append-only audit events for configuration, policy, waiver, and release decisions;
- service-catalog identity and ownership synchronization;
- governed pack publication, signatures, compatibility, promotion, and rollback;
- waiver request, approval, expiry, renewal, and revocation workflows;
- durable queues, bounded retries, idempotency, backpressure, and private collectors;
- notification and ticketing delivery with deduplication and failure handling;
- availability objectives, capacity limits, backups, restore tests, and disaster recovery;
- a versioned API with authentication, authorization, pagination, rate limits,
  idempotency, compatibility guarantees, and an end-of-life policy.

## Non-negotiable boundaries

- Runtime access remains explicitly configured, read-only, scoped, and auditable.
- Tenant data is never used across tenants for scoring or explanation.
- AI remains optional and cites existing Beacon evidence. It cannot create
  evidence, change scores, approve waivers, or decide a release gate.
- The control plane must not become a second source of truth for service ownership,
  telemetry, or incident records; integrations synchronize stable identifiers.
- A secure architecture and threat-model review is required before any networked beta.
