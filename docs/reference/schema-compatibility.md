# Event Schema Compatibility Standard

Example reference document used by Beacon intelligence-context examples.

Recommended production defaults:

- Schema Registry compatibility should not be `NONE`
- use `BACKWARD`, `FULL`, or an approved compatibility mode per subject
- producers should publish schema-compatible changes
- consumers should have a documented poison-message and DLQ strategy

