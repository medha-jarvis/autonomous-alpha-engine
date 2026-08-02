#!/usr/bin/env python3
"""Get Vercel deployment build logs."""
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

# Get deployment details  
uid = 'dpl_EQLCeWeG0Ua1xRZb7j9X2FhZ0aD7'
req = urllib.request.Request(
    f'https://api.vercel.com/v13/deployments/{uid}',
    headers=headers,
)
resp = urllib.request.urlopen(req, timeout=15)
dep = json.loads(resp.read())

print(f"State: {dep.get('readyState', '?')}")
print(f"Error: {dep.get('errorMessage', 'none')}")
print(f"Error Code: {dep.get('errorCode', 'none')}")
print(f"Created: {dep.get('createdAt', 0)}")
print(f"Building: {dep.get('buildingAt', 0)}")
print(f"Ready: {dep.get('readyAt', 0)}")

# Get build logs
try:
    req2 = urllib.request.Request(
        f'https://api.vercel.com/v1/deployments/{uid}/events?direction=forward',
        headers=headers,
    )
    resp2 = urllib.request.urlopen(req2, timeout=15)
    events = json.loads(resp2.read())
    print(f"\nBuild events ({len(events)}):")
    for event in events[-30:]:
        text = event.get('text', event.get('payload', {}).get('text', ''))
        if text:
            print(f"  {text[:200]}")
except Exception as e:
    print(f"\nLog error: {e}")

print(f"\nInspect: https://vercel.com/medha-jarvis/autonomous-alpha-engine/{uid}")