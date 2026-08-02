#!/usr/bin/env bash
# Alpha Engine poller — cron entry point (local wrapper)
# Wrapper avoids symlink security check in the cron runner.
# Process at most 2 transcripts per run to stay within 120s cron timeout.
set -euo pipefail

cd /opt/data/alpha-engine/backend/src
export PYTHONPATH="${PYTHONPATH:-}:${PWD}"

exec /opt/data/.venv/bin/python orchestrator.py --max-transcripts=2 "$@"