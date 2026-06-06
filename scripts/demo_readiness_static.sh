#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /Library/Developer/CommandLineTools/usr/bin/python3 ]]; then
    PYTHON_BIN=/Library/Developer/CommandLineTools/usr/bin/python3
  else
    PYTHON_BIN=python3
  fi
fi

DEMO_DIR="${DEMO_DIR:-reports/readiness-demo}"
mkdir -p "$DEMO_DIR"

section() {
  printf "\n\n== %s ==\n" "$1"
}

section "Beacon static production-readiness demo"
printf "Input: examples/bad-infra\n"
printf "Artifacts: %s\n" "$DEMO_DIR"

section "Run readiness scan and generate HTML report"
"$PYTHON_BIN" -m beacon.cli readiness static examples/bad-infra --no-open-report

section "Save JSON output for review or CI"
"$PYTHON_BIN" -m beacon.cli readiness static examples/bad-infra \
  --no-html \
  --no-open-report \
  --output json > "$DEMO_DIR/bad-infra-readiness.json"

section "Run UI smoke test for the same readiness path"
"$PYTHON_BIN" scripts/ui_smoke_check.py

section "Demo complete"
printf "HTML report: reports/report.html\n"
printf "JSON report: %s/bad-infra-readiness.json\n" "$DEMO_DIR"
