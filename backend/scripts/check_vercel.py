#!/usr/bin/env python3
"""Check Vercel deployment status and wait for it to complete."""
import json, urllib.request, urllib.error, os, sys, time

# Read token
vercel_token = ""
with open('/opt/data/.env') as f:
    for line in f:
        if 'VERCEL_TOKEN' in line and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                vercel_token = parts[1].strip()
                break

headers = {'Authorization': f'Bearer {vercel_token}'}

# First check deployments list
req = urllib.request.Request(
    'https://api.vercel.com/v6/deployments?projectId=prj_snfaHzA4s2FlFoIBE033yRLwx0JB&limit=1',
    headers=headers,
)
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
deployments = data.get('deployments', [])

if deployments:
    d = deployments[0]
    uid = d.get('uid', '')
    state = d.get('readyState', '?')
    url = d.get('url', 'auto..alpha..')
    created = d.get('createdAt', 0)
    print(f"Latest deployment: {uid[:12]}...")
    print(f"State: {state}")
    print(f"URL: https://{url}")
    print(f"Production: https://{d.get('alias', ['?'])[0] if d.get('alias') else '?'}")
    
    # Poll until ready
    max_attempts = 20
    for i in range(max_attempts):
        if state in ('READY', 'ERROR', 'CANCELED'):
            break
        time.sleep(5)
        req2 = urllib.request.Request(
            f'https://api.vercel.com/v13/deployments/{uid}',
            headers=headers,
        )
        resp2 = urllib.request.urlopen(req2, timeout=15)
        d2 = json.loads(resp2.read())
        state = d2.get('readyState', '?')
        print(f"  [{i+1}] State: {state}")
else:
    print("No deployments found yet")

print(f"\nFinal URL: https://autonomous-alpha-engine.vercel.app")
print(f"Deploy inspect: https://vercel.com/medha-jarvis/autonomous-alpha-engine/deployments")