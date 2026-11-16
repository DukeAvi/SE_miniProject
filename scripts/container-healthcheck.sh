#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
curl --fail --silent --show-error "http://127.0.0.1:${PORT}/healthz" >/dev/null
