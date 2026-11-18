#!/usr/bin/env bash
set -euo pipefail

ref="${GITHUB_REF:-}"
if [[ ! "$ref" =~ ^refs/tags/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
  echo "Release must use a semantic version tag such as v1.2.3; got '${ref:-unset}'." >&2
  exit 1
fi

echo "Validated release tag: ${ref#refs/tags/}"
