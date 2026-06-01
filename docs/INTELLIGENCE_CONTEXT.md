# Beacon Intelligence Context

Beacon can load a deterministic organization context file to make readiness interpretation environment-aware without letting AI decide readiness.

The deterministic engine still owns:

- rule execution
- severity
- score
- production decision
- grouped root-cause risks

The intelligence context can provide:

- environment profile
- organization name
- Kafka environment policy
- topic-pattern exceptions
- deterministic rule overrides
- references to future knowledge/RAG documents

Example:

```yaml
organization:
  name: Example Platform Team
  environment: dev

kafka_policy:
  dev:
    allow_single_broker: true
    allow_replication_factor_one: true
    require_owner_metadata: false
  prod:
    allow_single_broker: false
    allow_replication_factor_one: false
    require_owner_metadata: true

topic_patterns:
  "*.dlq":
    low_partitions_allowed: true
    severity: INFO
  "*.retry":
    low_partitions_allowed: true
    severity: INFO

rule_overrides:
  kafka.consumer_group.offsets.missing:
    severity: INFO
    reason: Missing offsets are observational unless the group is expected to be active.

knowledge_documents:
  - title: Kafka production standard
    path: docs/internal/kafka-production-standard.md
```

Use it from CLI:

```bash
python3 -m beacon.cli readiness kafka \
  --bootstrap-server localhost:9092 \
  --environment dev \
  --context examples/supported/intelligence/context.yaml \
  --no-open-report
```

Use it from the UI by uploading the context YAML/JSON in the **Intelligence context** field.

