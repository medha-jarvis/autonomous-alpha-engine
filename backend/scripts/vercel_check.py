#!/usr/bin/env python3
"""Check the successful deployment and assign production alias."""
import json, urllib.request, urllib.error, os, sys

vercel_token = ""
with open('/opt/data/.env') as f:
    for line in f:
        if 'VERCEL_TOKEN' in line and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                vercel_token = parts[1].strip()
                break

headers = {'Authorization': f'Bearer {vercel_token}', 'Content-Type': 'application/json'}

# Check the successful deployment
uid = 'dpl_B721pRpEnksxfPayzRQzF9agWNrE'
req = urllib.request.Request(
    f'https://api.vercel.com/v13/deployments/{uid}',
    headers=headers,
)
resp = urllib.request.urlopen(req, timeout=15)
dep = json.loads(resp.read())

url = dep.get('url', '?')
state = dep.get('readyState', '?')
aliases = dep.get('alias', [])
print(f"Deployment: {url}")
print(f"State: {state}")
print(f"Aliases: {aliases}")

# Test the URL
req2 = urllib.request.Request(f'https://{url}', headers={'User-Agent': 'Mozilla/5.0'})
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    print(f"HTTP: {resp2.status}")
    body = resp2.read()[:500].decode('utf-8', errors='replace')
    print(f"Content preview: {body[:200]}")
except Exception as e:
    print(f"Access error: {e}")

# Assign production alias
# First list domains
req3 = urllib.request.Request(
    'https://api.vercel.com/v9/projects/autonomous-alpha-engine/domains',
    headers=headers,
)
try:
    resp3 = urllib.request.urlopen(req3, timeout=15)
    domains = json.loads(resp3.read())
    print(f"\nDomains: {domains}")
except Exception as e:
    print(f"Domains error: {e}")

# Assign the production alias from project
assign_data = json.dumps({'alias': 'autonomous-alpha-engine.vercel.app'}).encode()
req4 = urllib.request.Request(
    f'https://api.vercel.com/v13/deployments/{uid}/aliases',
    data=assign_data,
    headers=headers,
)
try:
    resp4 = urllib.request.urlopen(req4, timeout=15)
    alias_result = json.loads(resp4.read())
    print(f"\nAlias result: {alias_result.get('alias', 'OK')}")
except urllib.error.HTTPError as e:
    err = e.read().decode()[:300]
    print(f"Alias error {e.code}: {err}")
    # Try without body
    try:
        req5 = urllib.request.Request(
            f'https://api.vercel.com/v9/projects/autonomous-alpha-engine/domains',
            data=json.dumps({'name': 'autonomous-alpha-engine.vercel.app'}).encode(),
            headers=headers,
        )
        resp5 = urllib.request.urlopen(req5, timeout=15)
        dom = json.loads(resp5.read())
        print(f"Domain created: {dom}")
        
        # Then assign
        req6 = urllib.request.Request(
            f'https://api.vercel.com/v13/deployments/{uid}/aliases',
            data=json.dumps({'alias': 'autonomous-alpha-engine.vercel.app'}).encode(),
            headers=headers,
        )
        resp6 = urllib.request.urlopen(req6, timeout=15)
        alias2 = json.loads(resp6.read())
        print(f"✅ Alias set: {alias2.get('alias', 'OK')}")
    except Exception as e2:
        print(f"Domain error: {e2}")

print(f"\nTry your deployment at: https://{url}")