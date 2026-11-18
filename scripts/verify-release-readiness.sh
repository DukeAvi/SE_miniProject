#!/usr/bin/env bash
set -euo pipefail

echo "Running linter checks..."
ruff check .

echo "Validating Django settings and pending migrations..."
python manage.py check --settings=bbms.settings_test
python manage.py makemigrations --check --dry-run --settings=bbms.settings_test

echo "Validating OpenAPI contract..."
python scripts/validate_api_contract.py

echo "Running test suite..."
pytest
