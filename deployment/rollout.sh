#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <image-tag> (e.g., v1.0.0)" >&2
  exit 1
fi

export BBMS_IMAGE_TAG="$1"
COMPOSE_FILES=(-f compose.yaml -f compose.secure.yaml -f deployment/compose.ghcr.yaml)

echo "Pulling BBMS release image tag: ${BBMS_IMAGE_TAG}..."
docker compose "${COMPOSE_FILES[@]}" pull web worker beat monitoring-config-check alert-receiver

echo "Applying database migrations..."
docker compose "${COMPOSE_FILES[@]}" run --rm web python manage.py migrate --noinput

echo "Rolling out updated containers..."
docker compose "${COMPOSE_FILES[@]}" up -d --wait --wait-timeout 120

echo "Verifying /healthz endpoint..."
docker compose "${COMPOSE_FILES[@]}" exec -T web python -c \
  "import os, urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/healthz', headers={'Host': os.environ['BBMS_PUBLIC_HOSTNAME'], 'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request, timeout=3)"
echo "Deployment of ${BBMS_IMAGE_TAG} succeeded."
