#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEMO_DIR="$(mktemp -d)"
trap 'rm -rf "${DEMO_DIR}"' EXIT

echo "== Beacon Product Readiness Demo =="

echo
echo "1) Good infra -> expected READY"
"$PYTHON_BIN" -m beacon.cli readiness static examples/product-readiness/good-infra \
  --environment prod \
  --evidence-output "${DEMO_DIR}/good-evidence.json" \
  --no-html \
  --no-open-report

echo
echo "2) Bad infra -> expected NOT READY"
set +e
"$PYTHON_BIN" -m beacon.cli readiness static examples/product-readiness/bad-infra \
  --environment prod \
  --evidence-output "${DEMO_DIR}/bad-evidence.json" \
  --no-html \
  --no-open-report \
  --ci \
  --fail-on critical
bad_status=$?
set -e
echo "Bad infra CI exit code: ${bad_status}"

echo
echo "3) Dev exception -> expected contextual downgrade / low risk"
"$PYTHON_BIN" -m beacon.cli readiness static examples/product-readiness/dev-exception \
  --environment dev \
  --policy examples/product-readiness/dev-exception/beacon-policy.yaml \
  --no-html \
  --no-open-report

echo
echo "4) Same shape in prod -> expected NOT READY or major production risk"
set +e
"$PYTHON_BIN" -m beacon.cli readiness static examples/product-readiness/prod-same-risk \
  --environment prod \
  --no-html \
  --no-open-report \
  --ci \
  --fail-on critical
prod_status=$?
set -e
echo "Prod same-risk CI exit code: ${prod_status}"

echo
echo "5) Release comparison -> bad infra compared with good infra"
"$PYTHON_BIN" -m beacon.cli compare \
  "${DEMO_DIR}/bad-evidence.json" \
  "${DEMO_DIR}/good-evidence.json"
