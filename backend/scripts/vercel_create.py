#!/usr/bin/env python3
"""Create Vercel project and deploy from GitHub."""
import json, urllib.request, urllib.error, os, sys

# Read Vercel token
vc_token = ""
vercel_token_line_val = None
with open('/opt/data/.env') as f:
    for line in f:
        if 'VERCEL_TOKEN' in line and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                val = parts[1].strip()
                if val and len(val) > 10:
                    vercel_token_line_val = val
                    break

if not vercel_token_line_val:
    try:
        with open(os.path.expanduser('~/.vercel/auth.json')) as f:
            auth = json.load(f)
            vercel_token_line_val = auth.get('token', '')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

vc_token = vercel_token_line_val
if not vc_token:
    print("ERROR: No Vercel token found")
    sys.exit(1)

print(f"Vercel token: {vc_token[:10]}... (len={len(vc_token)})")

headers = {
    'Authorization': f'Bearer {vc_token}',
    'Content-Type': 'application/json',
}

# Create project
project_data = {
    'name': 'autonomous-alpha-engine',
    'framework': 'nextjs',
    'gitRepository': {
        'repo': 'medha-jarvis/autonomous-alpha-engine',
        'type': 'github',
    },
    'environmentVariables': [
        {
            'key': 'TYPESENSE_URL',
            'value': 'http://31.97.227.135:8700',
            'target': ['production', 'preview', 'development'],
            'type': 'encrypted',
        },
        {
            'key': 'TYPESENSE_API_KEY',
            'value': 'alpha-engine-api-proxy-2026',
            'target': ['production', 'preview', 'development'],
            'type': 'encrypted',
        },
    ],
    'rootDirectory': 'frontend',
}

req = urllib.request.Request(
    'https://api.vercel.com/v9/projects',
    data=json.dumps(project_data).encode(),
    headers=headers,
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    proj = json.loads(resp.read())
    print(f"✅ Project: {proj.get('name', '?')}")
    print(f"   ID: {proj.get('id', '?')}")
except urllib.error.HTTPError as e:
    err_text = e.read().decode()[:300]
    print(f"Create error {e.code}: {err_text}")
    if 'already exists' in err_text or e.code == 409:
        print("Project already exists. Continuing...")
    else:
        sys.exit(1)

# Now trigger deployment from GitHub
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
        'buildCommand': 'npm run build',
        'outputDirectory': '.next',
    },
}

req2 = urllib.request.Request(
    'https://api.vercel.com/v13/deployments',
    data=json.dumps(deploy_data).encode(),
    headers=headers,
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=60)
    dep = json.loads(resp2.read())
    url = dep.get('url', '')
    state = dep.get('readyState', 'BUILDING')
    print(f"\n✅ DEPLOYMENT TRIGGERED!")
    print(f"   URL: https://{url}")
    print(f"   State: {state}")
    print(f"   Inspect: https://vercel.com/medha-jarvis/autonomous-alpha-engine/deployments")
except urllib.error.HTTPError as e:
    err_text = e.read().decode()[:500]
    print(f"Deploy error {e.code}:")
    print(err_text)

print(f"\nDashboard will be live at:")
print(f"   https://autonomous-alpha-engine.vercel.app")