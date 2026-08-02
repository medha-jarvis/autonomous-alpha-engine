#!/usr/bin/env bash
# Extract GitHub token from .env and push
set -euo pipefail

cd /opt/data/alpha-engine

# Read token via Python to avoid shell interpretation issues
GITHUB_TOKEN=$(python3 -c "
import re
with open('/opt/data/.env') as f:
    content = f.read()
m = re.search(r'GITHUB_TOKEN=(.+)', content)
print(m.group(1).strip() if m else '')
")

echo "Token length: ${#GITHUB_TOKEN}"

# Already have the remote from the init
git remote remove origin 2>/dev/null || true
git remote add origin "https://oauth2:${GITHUB_TOKEN}@github.com/medha-jarvis/autonomous-alpha-engine.git"

# Push
git push -u origin main --force 2>&1
echo "Exit code: $?"