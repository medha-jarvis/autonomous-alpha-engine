#!/usr/bin/env python3
"""Update existing Vercel env vars by ID."""
import json, urllib.request, urllib.error, os, sys

vercel_token = ""
with open('/opt/data/.env') as f:
    for line in f:
        if 'VERCEL_TOKEN' in line and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                val = parts[1].strip()
                if val:
                    vercel_token = val
                    break

headers = {'Authorization': f'Bearer {vercel_token}', 'Content-Type': 'application/json'}

# List env vars to get IDs
req = urllib.request.Request(
    'https://api.vercel.com/v9/projects/autonomous-alpha-engine/env?target=production',
    headers=headers,
)
resp = urllib.request.urlopen(req, timeout=15)
envs = json.loads(resp.read())
print("Current env vars:")
for env in envs.get('envs', []):
    print(f"  {env['key']} = {env.get('value', '?')} (id: {env['id']})")

# Delete old env vars
for env in envs.get('envs', []):
    if env['key'] in ('TYPESENSE_URL', 'TYPESENSE_API_KEY'):
        req2 = urllib.request.Request(
            f"https://api.vercel.com/v9/projects/autonomous-alpha-engine/env/{env['id']}",
            method='DELETE',
            headers=headers,
        )
        resp2 = urllib.request.urlopen(req2, timeout=15)
        print(f"Deleted {env['key']}")

# Create new env vars with correct values
new_envs = [
    {'key': 'TYPESENSE_URL', 'value': 'http://31.97.227.135:3000', 'target': ['production', 'preview', 'development'], 'type': 'encrypted'},
    {'key': 'TYPESENSE_API_KEY', 'value': 'alpha-secret-key-2026', 'target': ['production', 'preview', 'development'], 'type': 'encrypted'},
]

for ev in new_envs:
    req3 = urllib.request.Request(
        'https://api.vercel.com/v9/projects/autonomous-alpha-engine/env',
        data=json.dumps(ev).encode(),
        headers=headers,
    )
    resp3 = urllib.request.urlopen(req3, timeout=15)
    result = json.loads(resp3.read())
    print(f"✅ Created {ev['key']} = {ev['value']}")

print("\nEnv vars updated. Triggering deployment...")

# Trigger deployment
deploy_data = {
    'name': 'autonomous-alpha-engine',
    'project': 'autonomous-alpha-engine',
    'target': 'production',
    'gitSource': {'type': 'github', 'repoId': '1320151504', 'ref': 'main'},
    'projectSettings': {'framework': 'nextjs', 'rootDirectory': 'frontend'},
}

req4 = urllib.request.Request(
    'https://api.vercel.com/v13/deployments',
    data=json.dumps(deploy_data).encode(),
    headers=headers,
)
resp4 = urllib.request.urlopen(req4, timeout=60)
dep = json.loads(resp4.read())
print(f"\n✅ Deployed: https://{dep.get('url', '?')}")
print(f"✅ Production: https://autonomous-alpha-engine.vercel.app")