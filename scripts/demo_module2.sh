#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /Library/Developer/CommandLineTools/usr/bin/python3 ]]; then
    PYTHON_BIN=/Library/Developer/CommandLineTools/usr/bin/python3
  else
    PYTHON_BIN=python3
  fi
fi

section() {
  printf "\n\n== %s ==\n" "$1"
}

section "Module 2 diagnostic release gate"
"$PYTHON_BIN" scripts/module2_diagnostic_check.py

section "Kafka rebalance storm incident scenario"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/rebalance-storm-runtime.yaml \
  --no-html \
  --no-open-report

section "Kafka quota and throttling incident scenario"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/quota-throttle-runtime.yaml \
  --no-html \
  --no-open-report

section "Kafka schema or poison-message incident scenario"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-runtime \
  examples/supported/kafka/scenarios/schema-poison-runtime.yaml \
  --no-html \
  --no-open-report

section "Kafka history trend scenario"
"$PYTHON_BIN" -m beacon.cli diagnose kafka-history \
  examples/supported/kafka/scenarios/lag-rebalance-history.yaml \
  --no-html \
  --no-open-report
