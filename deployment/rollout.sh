#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <image-tag> (e.g., v1.0.0)" >&2
  exit 1
fi

export BBMS_IMAGE_TAG="$1"
COMPOSE_FILES=(-f compose.yaml -f compose.secure.yaml -f deployment/compose.ghcr.yaml)

echo "Pulling BBMS release image tag: ${BBMS_IMAGE_TAG}..."
docker compose "${COMPOSE_FILES[@]}" pull web worker beat monitoring-config-check

echo "Applying database migrations..."
docker compose "${COMPOSE_FILES[@]}" run --rm web python manage.py migrate --noinput

echo "Rolling out updated containers..."
docker compose "${COMPOSE_FILES[@]}" up -d --remove-orphans

echo "Verifying /healthz endpoint..."
curl --fail --retry 6 --retry-delay 3 http://127.0.0.1:8000/healthz
echo "Deployment of ${BBMS_IMAGE_TAG} succeeded."
