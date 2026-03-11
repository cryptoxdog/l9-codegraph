#!/usr/bin/env bash
set -euo pipefail

echo "Starting test dependencies..."
docker compose up -d --wait 2>/dev/null || true

echo "Running tests..."
pytest tests/ -v --tb=short "$@"
EXIT_CODE=$?

echo "Stopping test dependencies..."
docker compose down 2>/dev/null || true

exit $EXIT_CODE
