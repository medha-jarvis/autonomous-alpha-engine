#!/usr/bin/env python3
"""List Vercel deployments and get correct IDs."""
import json, urllib.request, urllib.error, os, sys

vercel_token = ""
with open('/opt/data/.env') as f:
    for line in f:
        if 'VERCEL_TOKEN' in line and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                vercel_token = parts[1].strip()
                break

headers = {'Authorization': f'Bearer {vercel_token}'}

req = urllib.request.Request(
    'https://api.vercel.com/v6/deployments?projectId=prj_snfaHzA4s2FlFoIBE033yRLwx0JB&limit=5',
    headers=headers,
)
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())

deployments = data.get('deployments', [])
print(f"Found {len(deployments)} deployments:")
for d in deployments:
    uid = d.get('uid', '?')
    state = d.get('readyState', '?')
    url = d.get('url', '?')
    created = d.get('createdAt', 0)
    aliases = d.get('alias', [])
    print(f"\n  ID: {uid}")
    print(f"  State: {state}")
    print(f"  URL: {url}")
    print(f"  Aliases: {aliases}")
    if state == 'ERROR':
        print(f"  Error: {d.get('errorMessage', 'unknown')}")
        print(f"  Error Code: {d.get('errorCode', '?')}")
        meta = d.get('meta', {})
        if meta.get('action'):
            print(f"  Action: {meta.get('action')}")