#!/usr/bin/env bash
set -euo pipefail

IMAGE="${BEACON_IMAGE:-beacon:local}"
PORT="${BEACON_PORT:-8765}"
MODE="${1:-ui}"

section() {
  printf "\n== %s ==\n" "$1"
}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the container demo."
  exit 1
fi

section "Build private-source Beacon image"
docker build -t "$IMAGE" .

case "$MODE" in
  ui)
    section "Run Beacon UI"
    echo "Open http://127.0.0.1:${PORT}"
    docker run --rm -p "${PORT}:8765" "$IMAGE" ui --host 0.0.0.0 --port 8765
    ;;
  readiness)
    section "Run project-local readiness"
    docker run --rm -v "$PWD:/workspace/project:ro" "$IMAGE" readiness \
      --config /workspace/project/beacon.yaml \
      --output terminal
    ;;
  demo)
    section "Run static readiness demo"
    docker run --rm -v "$PWD:/workspace/project:ro" "$IMAGE" readiness static \
      /workspace/project/examples/bad-infra \
      --no-html \
      --no-open-report
    ;;
  *)
    echo "Usage: $0 [ui|readiness|demo]"
    exit 1
    ;;
esac
