# Security Policy

## Supported versions

Security fixes are provided for the latest published Beacon minor release. A
release is supported only when its immutable tag appears in the official
distribution repository. Development branches and untagged builds are not
supported releases.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or include secrets,
credentials, customer data, or exploit details in Beacon reports.

Use GitHub private vulnerability reporting when it is enabled for this
repository. If it is unavailable, contact `mishraricha1806@gmail.com` with:

- the affected version or commit;
- the component and deployment mode;
- reproduction steps and impact;
- whether credentials or customer data may be exposed;
- a safe method for further communication.

The maintainers will acknowledge receipt, validate scope, coordinate remediation,
and publish an advisory when appropriate. Please allow time for a fix before
public disclosure.

## Security boundary

Beacon is a read-only analysis tool. Runtime credentials must be short-lived,
least-privileged, and scoped to explicitly selected resources. The local UI has
no authentication or authorization boundary and must not be exposed as a shared
service. See `docs/CONTROL_PLANE_ENTRY_CRITERIA.md` before designing any networked
deployment.

## Release integrity

Consumers should use immutable action SHAs, release tags, binary checksums, and
container digests. Do not treat `latest`, a mutable branch, or an unsigned local
build as an auditable release artifact.
