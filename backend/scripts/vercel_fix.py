#!/usr/bin/env python3
"""Update Vercel environment variables to point to the proxy on port 3000."""
import json, urllib.request, urllib.error, os, sys

# Read Vercel token
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

headers = {
    'Authorization': f'Bearer {vercel_token}',
    'Content-Type': 'application/json',
}

# Set env vars on the project
env_vars = [
    {'key': 'TYPESENSE_URL', 'value': 'http://31.97.227.135:3000', 'target': ['production'], 'type': 'encrypted'},
    {'key': 'TYPESENSE_API_KEY', 'value': 'alpha-secret-key-2026', 'target': ['production'], 'type': 'encrypted'},
]

for ev in env_vars:
    req = urllib.request.Request(
        f"https://api.vercel.com/v9/projects/autonomous-alpha-engine/env",
        data=json.dumps(ev).encode(),
        headers=headers,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        print(f"✅ Set {ev['key']} = {ev['value']}")
    except urllib.error.HTTPError as e:
        err_text = e.read().decode()[:200]
        # If already exists, try PATCH
        if e.code == 409 or 'already exists' in err_text:
            print(f"  {ev['key']}: already exists (checking...")
            # List env vars
            req2 = urllib.request.Request(
                "https://api.vercel.com/v9/projects/autonomous-alpha-engine/env?target=production",
                headers=headers,
            )
            resp2 = urllib.request.urlopen(req2, timeout=15)
            existing = json.loads(resp2.read())
            for ex in existing.get('envs', []):
                if ex.get('key') == ev['key']:
                    # Update
                    req3 = urllib.request.Request(
                        f"https://api.vercel.com/v9/projects/autonomous-alpha-engine/env/{ex['id']}",
                        data=json.dumps(ev).encode(),
                        headers=headers,
                        method='PATCH',
                    )
                    try:
                        resp3 = urllib.request.urlopen(req3, timeout=15)
                        print(f"  ✅ Updated {ev['key']}")
                    except Exception as e3:
                        print(f"  ❌ Update failed: {e3}")
        else:
            print(f"  ❌ Error {e.code}: {err_text}")

print("\nNow redeploying from GitHub...")

# Trigger new deployment from GitHub
deploy_data = {
    'name': 'autonomous-alpha-engine',
    'project': 'autonomous-alpha-engine',
    'target': 'production',
    'gitSource': {
        'type': 'github',
        'repoId': '1320151504',
        'ref': 'main',
    },
    'projectSettings': {
        'framework': 'nextjs',
        'rootDirectory': 'frontend',
    },
}

req4 = urllib.request.Request(
    'https://api.vercel.com/v13/deployments',
    data=json.dumps(deploy_data).encode(),
    headers=headers,
)
try:
    resp4 = urllib.request.urlopen(req4, timeout=60)
    dep = json.loads(resp4.read())
    url = dep.get('url', '')
    print(f"\n✅ Redeployment triggered!")
    print(f"   Staging URL: https://{url}")
except urllib.error.HTTPError as e:
    err_text = e.read().decode()[:300]
    print(f"\nDeploy error {e.code}: {err_text}")

print(f"\nProduction URL: https://autonomous-alpha-engine.vercel.app")
print("(May take 1-2 minutes for the build to complete)")