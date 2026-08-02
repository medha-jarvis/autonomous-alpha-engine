#!/usr/bin/env bash
# Run the Alpha Engine poller (cron entry point)
set -euo pipefail

cd "$(dirname "$0")/../src"
export PYTHONPATH="${PYTHONPATH:-}:${PWD}"

exec /opt/data/.venv/bin/python orchestrator.py "$@"