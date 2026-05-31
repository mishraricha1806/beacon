# Beacon Kafka Release Guide

Kafka is Beacon's first deep runtime and readiness domain. This guide defines the supported Kafka input contract, release commands, permissions, examples, and known limits.

## Supported Inputs

Beacon supports these Kafka readiness inputs:

- Static Kafka broker, topic, producer, and consumer YAML.
- Read-only live Kafka metadata, topic config, broker config, consumer group, lag, ACL, quota, and member churn collection.
- Generic Kafka access profiles for cluster, topic, and consumer-group scoped credentials.
- Schema Registry collector YAML with bearer, basic, custom CA, and mTLS support.
- Offline Kafka ACL exports in YAML or JSON.
- Kafka runtime history snapshots in YAML or JSON.
- Prometheus/JMX-derived Kafka runtime signals.
- Kafka runtime snapshot YAML.

## Static Kafka Config

Use this for pre-production checks from config files:

```bash
python3 -m beacon.cli readiness static examples/supported/kafka --no-html --no-open-report
```

Static Kafka YAML may contain:

```yaml
kafka:
  brokers:
    - id: 1
      default_replication_factor: 3
      listener_security_protocol_map: SSL:SSL
      authorizer_class_name: kafka.security.authorizer.AclAuthorizer
      allow_everyone_if_no_acl_found: false
  topics:
    - name: payments
      replication_factor: 3
      partitions: 12
      retention_bytes: 10737418240
      min_insync_replicas: 2
      schema_compatibility: BACKWARD
      owner: payments-platform
  producers:
    - name: checkout-producer
      topic: payments
      acks: all
      enable_idempotence: true
  consumers:
    - name: payment-worker
      topic: payments
      group_id: payment-worker
      enable_auto_commit: false
      auto_offset_reset: earliest
      retry_max_attempts: 5
      dlq_topic: payments-dlq
```

## Live Kafka Collection

Live Kafka collection is read-only. Beacon lists metadata, describes configs, reads offsets, describes groups, describes ACLs when permitted, and samples group membership when requested.

```bash
python3 -m beacon.cli readiness kafka \
  --bootstrap-server localhost:9092 \
  --security-protocol SSL \
  --ca-cert ./ca.pem \
  --client-cert ./client.pem \
  --client-key ./client.key \
  --consumer-group payment-worker \
  --churn-samples 3 \
  --churn-interval-seconds 2 \
  --no-html \
  --no-open-report
```

Beacon does not produce, consume, alter topics, reset offsets, mutate ACLs, or change infrastructure.

## Generic Access Profiles

Use access profiles when an organization has different credentials for cluster discovery, topic config, and consumer-group diagnostics.

```bash
python3 -m beacon.cli readiness kafka \
  --access-config examples/supported/kafka/access-profiles.yaml \
  --topic payments \
  --consumer-group payment-worker \
  --no-html \
  --no-open-report
```

Access profiles support scoped capabilities, topic/group patterns, mTLS, bearer token, SASL, and least-privilege posture checks.

## Schema Registry

Schema Registry diagnostics are read-only and query subjects, compatibility config, expected topic subjects, and latest schemas.

```bash
python3 -m beacon.cli readiness schema-registry \
  examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report
```

Schema Registry YAML may contain:

```yaml
schema_registry:
  url: https://schema-registry.local:8081
  max_subjects: 25
  auth:
    type: bearer_token
    token: example-read-only-token
  tls:
    ca_cert: ./ca.pem
    client_cert: ./client.pem
    client_key: ./client.key
  expected_topics:
    - name: payments
      subjects:
        - payments-key
        - payments-value
```

## Offline ACL Exports

Use offline ACL exports when live `DescribeAcls` is not allowed.

```bash
python3 -m beacon.cli readiness kafka-acls \
  examples/supported/kafka/acls.yaml \
  --no-html \
  --no-open-report
```

Supported shapes:

```yaml
kafka_acls:
  - principal: User:payments-service
    host: "*"
    operation: READ
    permission_type: ALLOW
    resource_type: TOPIC
    resource_name: payments
    resource_pattern_type: LITERAL
```

Beacon detects empty ACL exports and broad wildcard/all-operation allow permissions.

## Kafka History

Kafka history catches trends that one snapshot cannot prove.

```bash
python3 -m beacon.cli readiness kafka-history \
  examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report
```

Supported shape:

```yaml
kafka_history:
  - timestamp: "2026-05-31T10:00:00Z"
    broker_disk_usage_percent: 73
    total_consumer_lag: 15000
    controller_change_count_15m: 0
    rebalance_count_15m: 0
    consumer_groups:
      - group_id: payments-worker
        members: [worker-a]
```

Beacon detects growing disk usage, growing lag, controller churn, rebalance churn, and member churn.

## Prometheus/JMX Runtime Signals

Use Prometheus configs to map JMX and platform metrics into deterministic Kafka runtime checks:

```bash
python3 -m beacon.cli readiness prometheus \
  examples/supported/prometheus/kafka-jmx-prometheus.yaml \
  --no-html \
  --no-open-report
```

## Scenario Pack

Kafka scenarios live under `examples/supported/kafka/scenarios/`:

- `unsafe-security.yaml` checks plaintext listeners, weak broker defaults, missing authorization, and missing quotas.
- `unsafe-acls.yaml` checks broad ACLs through the offline ACL scanner.
- `lag-rebalance-history.yaml` checks lag growth, controller churn, rebalance churn, and member churn.
- `schema-poison-risk.yaml` checks unsafe schema compatibility, weak producer durability, risky consumer offsets, and missing DLQ.

Run them:

```bash
python3 -m beacon.cli readiness static examples/supported/kafka/scenarios/unsafe-security.yaml --no-html --no-open-report
python3 -m beacon.cli readiness kafka-acls examples/supported/kafka/scenarios/unsafe-acls.yaml --no-html --no-open-report
python3 -m beacon.cli readiness kafka-history examples/supported/kafka/scenarios/lag-rebalance-history.yaml --no-html --no-open-report
python3 -m beacon.cli readiness static examples/supported/kafka/scenarios/schema-poison-risk.yaml --no-html --no-open-report
```

## Permissions

Live Kafka checks need only read-only permissions:

- Cluster metadata/list topics.
- Describe topic configs.
- Describe broker configs.
- List/describe consumer groups.
- List group offsets and latest offsets.
- Describe ACLs, optional.

If `DescribeAcls` is blocked, use an offline ACL export.

## Release Checklist

- Static Kafka examples produce deterministic findings.
- Live Kafka connector emits read-only mode finding.
- Access profile validation handles scoped org credentials.
- Schema Registry diagnostics support bearer, basic, custom CA, and mTLS.
- ACL export scanner handles broad allow and empty exports.
- Kafka history scanner detects worsening operational trends.
- Prometheus/JMX sample maps Kafka runtime signals.
- UI exposes Kafka live, Schema Registry, ACL export, and history inputs.
- Full test suite and Module 1 release gate pass.

## Known Limits

- Beacon does not mutate Kafka or remediate settings.
- Live ACL checks depend on `DescribeAcls`; offline export is the fallback.
- Churn sampling is best-effort and depends on the selected sample window.
- History diagnostics require at least two snapshots.
- Beacon does not yet persist history automatically; upload history exports for trend checks.
