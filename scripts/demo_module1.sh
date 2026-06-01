#!/usr/bin/env bash
set -euo pipefail

section() {
  printf "\n\n== %s ==\n" "$1"
}

section "Module 1 static readiness over supported examples"
python3 -m beacon.cli readiness static examples/supported --no-open-report

section "Module 1 all-domain readiness bundle"
python3 -m beacon.cli readiness all \
  --static-path examples/supported \
  --snapshot examples/supported/runtime/all-runtime.yaml \
  --opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --schema-registry examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report

section "Bad infrastructure regression should be NOT READY"
python3 -m beacon.cli readiness static examples/bad-infra \
  --no-html \
  --no-open-report

section "Runtime snapshot readiness"
python3 -m beacon.cli readiness snapshot examples/supported/runtime/all-runtime.yaml \
  --no-html \
  --no-open-report

section "Flow intelligence readiness"
python3 -m beacon.cli readiness flow examples/supported/runtime/flow-runtime.yaml \
  --no-html \
  --no-open-report

section "Kafka ACL export readiness"
python3 -m beacon.cli readiness kafka-acls examples/supported/kafka/acls.yaml \
  --no-html \
  --no-open-report

section "Kafka history trend readiness"
python3 -m beacon.cli readiness kafka-history examples/supported/kafka/history.yaml \
  --no-html \
  --no-open-report

section "OpenTelemetry runtime readiness"
python3 -m beacon.cli readiness opentelemetry examples/supported/opentelemetry/checkout-otel.yaml \
  --no-html \
  --no-open-report

section "Schema Registry readiness config"
python3 -m beacon.cli readiness schema-registry examples/supported/kafka/schema-registry.yaml \
  --no-html \
  --no-open-report

section "Rule metadata catalog"
python3 -m beacon.cli rules list --output json
