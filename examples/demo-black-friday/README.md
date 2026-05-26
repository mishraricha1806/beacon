# Demo Scenario: Black Friday Payment System

## Objective

Demonstrate Beacon's capability to evaluate an e-commerce payment processing system before a major traffic event (Black Friday).

**Question:** Can this Kafka topology survive Black Friday traffic spikes and operational failures?

---

## Scenario Setup

### System Architecture
Payment API ↓ ├─→ payments-topic (Kafka) ├─→ transactions-topic (Kafka) └─→ events-topic (Kafka) ↓ payment-processor (consumer) ↓ Payment Database

Code

### Challenge

The e-commerce company expects:
- **10x normal traffic** during Black Friday (100K → 1M transactions/day)
- **99.9% availability** during the event
- **Zero payment data loss** tolerance
- **<5s payment confirmation** latency

**The Question:** Is the infrastructure ready?

---

## PHASE 1: Static Infrastructure Analysis

### Input: Static Configuration

File: `kafka-config.yaml`

```
python3 -m beacon.cli readiness static ./examples/demo-black-friday/kafka-config.yaml  
```

Static Analysis Findings

```
Production Readiness Score: 52/100

CRITICAL:
  ❌ Kafka topic 'payments' has replication factor 1
     → Impact: Single broker failure loses payment data
     → Action: Increase to RF=3 minimum

  ❌ Kafka topic 'transactions' missing min.insync.replicas
     → Impact: Durability not guaranteed during failure
     → Action: Set min_insync_replicas=2

HIGH:
  ⚠️  Kafka topics have no retention_bytes limit
     → Impact: Unbounded disk growth during traffic spike
     → Action: Set retention_bytes=500GB based on 10 days retention

  ⚠️  Payment database connection pool too small (10 connections)
     → Impact: Bottleneck under 10x traffic load
     → Action: Increase to 100 connections

  ⚠️  No partition rebalancing plan
     → Impact: Uneven traffic distribution
     → Action: Pre-partition with 12 partitions per topic

MEDIUM:
  ⚡ Terraform lacks encryption for RDS database
  ⚡ S3 buckets missing versioning for audit logs
  ⚡ IAM policies too broad (Action: *)

PRODUCTION DECISION: ❌ NOT READY

```
Phase 1 Remediation

Actions taken:

✅ Increase payments-topic RF to 3
✅ Add min_insync_replicas=2 to all topics
✅ Set retention_bytes=536870912 (500GB)
✅ Increase DB pool to 100 connections
✅ Partition topics to 12 partitions each
✅ Enable RDS encryption
✅ Enable S3 versioning
✅ Apply least-privilege IAM policies

PHASE 2: Runtime Diagnostics

After static fixes, deploy to staging and analyze live behavior:

```
python3 -m beacon.cli diagnose kafka \
  --bootstrap-server kafka.staging:9092 \
  --topic payments
 ```
Runtime Findings (Pre-Load Test)

```
Production Readiness Score: 78/100

HIGH:
  ⚠️  High Kafka consumer lag detected for 'payment-processor'
     → Current lag: 2,500 messages
     → Lag trend: INCREASING over last 30 minutes
     → Broker health: HEALTHY
     → Producer throughput: 1,000 msg/sec
     → Consumer throughput: 800 msg/sec
     
     ROOT CAUSE: Consumer processing latency
     RECOMMENDATION: Investigate payment-processor logs for DB query slowness

  ⚠️  Partition 0 receiving 65% of traffic (hot partition)
     → Partition distribution is unbalanced
     → Partition key strategy: user_id (causing hot key)
     
     ROOT CAUSE: User hotspot (VIP customer account)
     RECOMMENDATION: Review partition key to balance by merchant_id

  ⚠️  Broker disk usage at 72% and growing at 2.5% per day
     → Current: 720GB used of 1TB
     → Estimated saturation: 11 days
     → During peak: Could hit saturation in 5 days
     
     ROOT CAUSE: Producer payload size increased 3x
     RECOMMENDATION: Review payload size, enable compression

PRODUCTION DECISION: ⚠️  CONDITIONAL READY
```

Phase 2 Remediation

Actions taken:

✅ Optimize payment-processor DB queries (added indices)
✅ Changed partition key from user_id to merchant_id
✅ Enabled compression (snappy)
✅ Increased broker storage to 2TB
✅ Added 2 new consumer instances (scale to 6 total)
PHASE 3: Snapshot Analysis & Capacity Planning

Collect 7 days of runtime metrics during load testing:

```
python3 -m beacon.cli runtime ./examples/demo-black-friday/7-day-snapshot.yaml
```
Snapshot Findings

```
Production Readiness Score: 91/100

Capacity Analysis:
  ✅ Storage growth: 3% per day (under control)
  ✅ Consumer lag: Stable at 100-200 messages
  ✅ Broker replication: All ISR intact
  ✅ Partition distribution: Balanced (±15%)
  ✅ Hot partition ratio: Reduced from 65% to 42%

Predictions (10x traffic):
  📊 Disk usage will reach 92% during peak
  📊 Processing latency will increase to 2.5s (acceptable <5s)
  📊 Consumer lag will spike to 5,000 messages but recover within 10 min
  📊 No broker rebalancing needed (partition distribution stable)

Risk Assessment:
  ✅ Storage: SAFE (headroom to 1.5TB)
  ✅ Throughput: READY (can handle 2M msg/day)
  ✅ Latency: READY (p99 latency = 3.2s)
  ✅ Availability: READY (replication keeps data safe)
  ✅ Recovery: READY (ISR rebalance <30 seconds)

CONTINGENCY PLANS:
  1. If disk hits 95%: Enable tiered storage to S3
  2. If lag spike >10K: Auto-scale consumers to 10 instances
  3. If broker failure: ISR failover within 20 seconds
  4. If partition skew >60%: Manual rebalance to 18 partitions

PRODUCTION DECISION: ✅ READY FOR BLACK FRIDAY
```
Final Production Decision

```
═══════════════════════════════════════════════════════════════
BEACON PRODUCTION DECISION
═══════════════════════════════════════════════════════════════

DECISION: ✅ READY FOR PRODUCTION

Production Readiness Score: 91/100

Analysis Type: Complete (Static + Runtime + Snapshot)

═══════════════════════════════════════════════════════════════
PRIMARY RISK AREAS
═══════════════════════════════════════════════════════════════

[MEDIUM] Storage Capacity
       Current usage: 72% of 2TB
       Growth rate: 3% per day
       Headroom: Sufficient for 14 days at peak load
       Action: Monitor daily; expand if exceeds 85%

[LOW] Partition Skew
       Current skew: 42% on hot partition
       Trend: Improving (was 65%)
       Action: Continue monitoring partition key strategy

═══════════════════════════════════════════════════════════════
NEXT BEST ACTIONS (Prioritized)
═══════════════════════════════════════════════════════════════

1. [MEDIUM] Finalize contingency runbooks for:
   • Disk saturation response
   • Consumer lag recovery procedures
   • Broker failure failover
   Effort: 4 hours | Impact: High | Priority: Before launch

2. [MEDIUM] Set up real-time alerting for:
   • Disk usage >85%
   • Consumer lag >5,000 messages
   • Broker unavailability
   • Partition skew >60%
   Effort: 2 hours | Impact: High | Priority: Before launch

3. [LOW] Schedule post-launch review:
   • Actual vs. predicted metrics
   • Consumer processing performance
   • Partition distribution stability
   Effort: 1 hour | Impact: Medium | Priority: 24 hours post-launch

4. [LOW] Plan for infrastructure expansion:
   • Add 1TB storage (current 2TB → 3TB)
   • Consider partition increase to 18
   • Evaluate broker upgrade path
   Effort: 8 hours | Impact: Medium | Priority: Post Black Friday

═══════════════════════════════════════════════════════════════

✅ LAUNCH APPROVED FOR BLACK FRIDAY

Confidence: HIGH (91/100)
Risk Level: LOW with established contingency
Readiness: All critical systems verified

═══════════════════════════════════════════════════════════════
```

How to Run This Demo

1. Static Analysis Phase

bash
# Scan infrastructure configuration
python3 -m beacon.cli readiness static ./examples/demo-black-friday/kafka-config.yaml

# View results
open reports/report.html
2. Runtime Analysis Phase

bash
# Diagnose live Kafka cluster (requires running Kafka)
python3 -m beacon.cli readiness kafka \
--bootstrap-server localhost:9092

# View results
open reports/report.html
3. Snapshot Analysis Phase

bash
# Analyze historical snapshot
python3 -m beacon.cli runtime ./examples/demo-black-friday/7-day-snapshot.yaml

# View results
open reports/report.html
4. Generate Complete Report

bash
# All analyses in one command (shows final decision)
python3 -m beacon.cli readiness static ./examples/demo-black-friday/kafka-config.yaml \
&& python3 -m beacon.cli runtime ./examples/demo-black-friday/7-day-snapshot.yaml
Key Learnings

Static Analysis catches architectural issues early (replication, retention)
Runtime Diagnostics reveal real-world bottlenecks (consumer lag, hot partitions)
Snapshot Analysis predicts failure modes under stress (capacity planning)
Deterministic Intelligence (no AI guessing) → trustworthy for production decisions
Clear Recommendations → engineers know exactly what to fix