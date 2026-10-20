# Contributing to Beacon

Beacon is proprietary. Contributions require repository access and acceptance
of the applicable organizational intellectual-property terms.

## Development workflow

1. Create a focused branch from the current default branch.
2. Keep collectors read-only and deterministic.
3. Add or update rule metadata for every emitted rule ID.
4. Add fixtures and tests for behavioral and contract changes.
5. Test supported Python versions 3.10 through 3.12.
6. Run `python scripts/release_check_all.py` and `beacon packs validate`.
7. Run `python scripts/quality_ratchet.py` and lower the baseline when debt is removed.
8. Update public schemas and compatibility documentation for contract changes.
9. Open a pull request with the risk, evidence, verification, and rollout plan.

## Product principles

- Findings must cite inspected evidence.
- Missing evidence must not be interpreted as a passing control.
- AI may explain existing evidence but cannot invent evidence or decide a gate.
- Runtime access must remain opt-in, scoped, short-lived, and read-only.
- Rules need an owner, rationale, remediation, severity, and stable identifier.
- Breaking public-contract changes require a new major schema version.

## Review requirements

Changes affecting authentication, secrets, runtime collection, release gates,
artifact distribution, public schemas, or tenant boundaries require a security
review. Changes to governed packs require review from their declared owner.

Do not commit credentials, customer data, generated reports, virtual
environments, or local runtime exports.
