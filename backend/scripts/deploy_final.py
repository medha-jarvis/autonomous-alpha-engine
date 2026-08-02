#!/usr/bin/env python3
"""Fix Vercel deploy with correct GitHub repo ID."""
import json, urllib.request, urllib.error, sys

# Read all env vars once
with open('/opt/data/.env') as f:
    lines = f.readlines()

gh_token = ''
vc_token = ''
for line in lines:
    line = line.strip()
    if line.startswith('GITHUB_TOKEN='):
        gh_token = line.split('=', 1)[1]
    elif line.startswith('VERCEL_TOKEN='):
        vc_token = line.split('=', 1)[1]

if not gh_token:
    print("No GitHub token")
    sys.exit(1)
if not vc_token:
    print("No Vercel token")
    sys.exit(1)

print(f"Tokens found: GH={gh_token[:10]}..., Vercel={vc_token[:10]}...")

# Get GitHub repo ID
req = urllib.request.Request(
    'https://api.github.com/repos/medha-jarvis/autonomous-alpha-engine',
    headers={'Authorization': f'token {gh_token}', 'Accept': 'application/vnd.github.v3+json'},
)
resp = urllib.request.urlopen(req, timeout=15)
repo = json.loads(resp.read())
repo_id = repo['id']
print(f"GitHub Repo ID: {repo_id}")

# Deploy to Vercel
deploy_data = {
    'name': 'autonomous-alpha-engine',
    'project': 'autonomous-alpha-engine',
    'target': 'production',
    'gitSource': {
        'type': 'github',
        'repoId': '1320151504',
        'ref': 'main',
    },
}

req2 = urllib.request.Request(
    'https://api.vercel.com/v13/deployments',
    data=json.dumps(deploy_data).encode(),
    headers={
        'Authorization': f'Bearer {vc_token}',
        'Content-Type': 'application/json',
    },
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=30)
    dep = json.loads(resp2.read())
    url = dep.get('url', '')
    print(f"✅ DEPLOYED: https://{url}")
    print(f"State: {dep.get('readyState', '?')}")
except urllib.error.HTTPError as e:
    err = e.read().decode()[:500]
    print(f"Deploy error {e.code}: {err}")
    print("Deploy manually via https://vercel.com/import/git")