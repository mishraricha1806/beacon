#!/usr/bin/env bash
set -euo pipefail

IMAGE="${BEACON_IMAGE:-ghcr.io/mishraricha1806/beacon}"
VERSION="${BEACON_VERSION:-$(python3 - <<'PY'
from pathlib import Path

pyproject = Path("pyproject.toml")
if pyproject.exists():
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version"):
            print(line.split("=", 1)[1].strip().strip('"'))
            raise SystemExit

print(Path("VERSION").read_text(encoding="utf-8").strip())
PY
)}"
OWNER="${GHCR_OWNER:-mishraricha1806}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required."
  exit 1
fi

echo "Building ${IMAGE}:${VERSION}"
docker build -t "${IMAGE}:${VERSION}" -t "${IMAGE}:latest" .

if [ -n "${GHCR_TOKEN:-}" ]; then
  echo "Logging in to ghcr.io as ${OWNER}"
  printf '%s' "${GHCR_TOKEN}" | docker login ghcr.io -u "${OWNER}" --password-stdin
fi

echo "Pushing ${IMAGE}:${VERSION}"
docker push "${IMAGE}:${VERSION}"

echo "Pushing ${IMAGE}:latest"
docker push "${IMAGE}:latest"

echo
echo "Published:"
echo "  ${IMAGE}:${VERSION}"
echo "  ${IMAGE}:latest"
