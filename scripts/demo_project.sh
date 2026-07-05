#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /Library/Developer/CommandLineTools/usr/bin/python3 ]]; then
    PYTHON_BIN=/Library/Developer/CommandLineTools/usr/bin/python3
  else
    PYTHON_BIN=python3
  fi
fi

DEMO_DIR="${DEMO_DIR:-reports/project-demo}"
mkdir -p "$DEMO_DIR"

section() {
  printf "\n\n== %s ==\n" "$1"
}

section "Beacon demo setup"
printf "Python: %s\n" "$PYTHON_BIN"
printf "Artifacts: %s\n" "$DEMO_DIR"

section "1. Module 1: production readiness over supported infrastructure"
"$PYTHON_BIN" -m beacon.cli readiness static examples/supported \
  --environment prod \
  --context examples/supported/intelligence/context.yaml \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli readiness static examples/supported \
  --environment prod \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module1-readiness-supported.json"

section "2. Module 1: environment-aware interpretation for intentionally weak dev infrastructure"
"$PYTHON_BIN" -m beacon.cli readiness static examples/bad-infra \
  --environment dev \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli readiness static examples/bad-infra \
  --environment dev \
  --context examples/supported/intelligence/context.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module1-dev-context.json"

section "3. Module 2: Kafka incident diagnosis - quota and throttling"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/quota-throttle-runtime.yaml \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/quota-throttle-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module2-quota-throttling.json"

section "4. Module 2: Kafka incident diagnosis - rebalance storm"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module2-rebalance-storm.json"

section "5. Module 3: flow intelligence - downstream bottleneck"
"$PYTHON_BIN" -m beacon.cli diagnose flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module3-flow-bottleneck.json"

section "6. End-to-end operational intelligence bundle"
"$PYTHON_BIN" -m beacon.cli diagnose all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --flow examples/supported/runtime/flow-runtime.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --kafka-acls examples/supported/kafka/acls.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --flow examples/supported/runtime/flow-runtime.yaml \
  --deployment-events examples/supported/deployments/events.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --kafka-acls examples/supported/kafka/acls.yaml \
  --kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/end-to-end-diagnostics.json"

section "7. Module 4: operational decisions - rollback before scale"
"$PYTHON_BIN" -m beacon.cli diagnose deployment-events \
  examples/supported/module4/rollback-vs-scale-deployment.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose deployment-events \
  examples/supported/module4/rollback-vs-scale-deployment.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module4-rollback-before-scale.json"

section "8. Module 4: operational decisions - Kafka client pressure before broker expansion"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/module4/kafka-client-pressure-runtime.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/module4/kafka-client-pressure-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module4-kafka-client-pressure.json"

section "9. Module 4: operational decisions - retention cleanup before storage expansion"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/module4/retention-cleanup-runtime.yaml \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/module4/retention-cleanup-runtime.yaml \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module4-retention-cleanup.json"

section "10. Module 4: operational decisions - Kubernetes security before rollout"
"$PYTHON_BIN" -m beacon.cli readiness static \
  examples/supported/module4/kubernetes-security-readiness.yaml \
  --environment prod \
  --no-html \
  --no-open-report

"$PYTHON_BIN" -m beacon.cli readiness static \
  examples/supported/module4/kubernetes-security-readiness.yaml \
  --environment prod \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/module4-kubernetes-security.json"

section "11. Release confidence gates"
"$PYTHON_BIN" scripts/module1_release_check.py
"$PYTHON_BIN" scripts/module2_diagnostic_check.py
"$PYTHON_BIN" scripts/module3_flow_check.py
"$PYTHON_BIN" scripts/module4_decision_check.py

section "Demo complete"
printf "Generated JSON artifacts:\n"
find "$DEMO_DIR" -maxdepth 1 -type f -name '*.json' | sort
printf "\nOpen the latest HTML report at reports/report.html if HTML generation was enabled in your run.\n"
