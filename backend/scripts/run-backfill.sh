#!/usr/bin/env bash
# Run backfill for all portfolio stocks
set -euo pipefail

cd "$(dirname "$0")/../src"
export PYTHONPATH="${PYTHONPATH:-}:${PWD}"

exec /opt/data/.venv/bin/python orchestrator.py backfill "$@"