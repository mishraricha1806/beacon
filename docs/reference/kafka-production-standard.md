# Kafka Production Standard

Example reference document used by Beacon intelligence-context examples.

Recommended production defaults:

- replication factor at least 3
- `min.insync.replicas` at least 2
- TLS for client and broker traffic
- explicit retention policy per topic
- owner/runbook metadata for production topics

