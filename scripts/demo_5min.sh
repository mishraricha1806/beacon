#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
fi

if ! "$PYTHON" -c "import typer, yaml, rich" >/dev/null 2>&1; then
  echo "Beacon Python dependencies are not available for: $PYTHON" >&2
  echo >&2
  echo "Install them with one of these commands, then rerun this script:" >&2
  echo "  python3 -m pip install -e ." >&2
  echo "  python3 -m pip install -r requirements.txt" >&2
  echo >&2
  echo "Or use the Docker quickstart in QUICKSTART_5_MINUTES.md." >&2
  exit 1
fi

echo "== Beacon 5-minute demo =="
echo
echo "This demo uses only local example files. No cloud, Kafka, Kubernetes, or"
echo "production credentials are required."
echo

echo "== 1. Distributed-system production readiness =="
"$PYTHON" -m beacon.cli readiness static \
  examples/product-readiness/distributed-infra-risk \
  --environment prod \
  --no-html \
  --no-open-report

echo
echo "== 2. IaC coverage readiness =="
"$PYTHON" -m beacon.cli readiness iac-coverage \
  --cloud-inventory examples/iac-coverage/aws-inventory.json \
  --terraform-state-dir examples/iac-coverage/states \
  --owners examples/iac-coverage/owners.yaml \
  --environment prod \
  --no-html \
  --no-open-report

echo
echo "== 3. Inspectable readiness pack =="
"$PYTHON" -m beacon.cli packs show distributed-system-production-readiness

echo
echo "== Demo complete =="
echo "Beacon should have shown a production-readiness decision, grouped risks,"
echo "operational decisions, and an inspectable pack definition."
