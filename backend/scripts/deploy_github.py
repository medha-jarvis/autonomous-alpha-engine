#!/usr/bin/env python3
"""Delete and recreate GitHub repo, then push clean code."""
import subprocess, json, re, urllib.request, urllib.error, os, sys

# Read token
with open('/opt/data/.env') as f:
    content = f.read()
m = re.search(r'GITHUB_TOKEN=(\S+)', content)
token = m.group(1).strip() if m else ''
print(f"Token: {token[:10]}... len={len(token)}")

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
}

# Delete repo
req = urllib.request.Request(
    'https://api.github.com/repos/medha-jarvis/autonomous-alpha-engine',
    method='DELETE', headers=headers)
try:
    resp = urllib.request.urlopen(req)
    print(f"Deleted: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Delete: {e.code} — {e.read().decode()[:100]}")

# Wait
import time
time.sleep(1)

# Create repo
data = json.dumps({
    'name': 'autonomous-alpha-engine',
    'description': 'Concall transcript intelligence with 20 AI evaluation pipelines',
    'private': False
}).encode()
req2 = urllib.request.Request(
    'https://api.github.com/user/repos',
    data=data, headers={**headers, 'Content-Type': 'application/json'})
try:
    resp2 = urllib.request.urlopen(req2)
    result = json.loads(resp2.read())
    print(f"Created: {result.get('html_url', 'OK')}")
except urllib.error.HTTPError as e:
    print(f"Create error: {e.code} {e.read().decode()[:200]}")
    sys.exit(1)

# Now push clean code
os.chdir('/opt/data/alpha-engine')
# Remove git and init fresh
subprocess.run(['rm', '-rf', '.git'], capture_output=True)
subprocess.run(['git', 'init', '-b', 'main'], capture_output=True)
subprocess.run(['git', 'config', 'user.name', 'Vishal Barfiwala'], capture_output=True)
subprocess.run(['git', 'config', 'user.email', 'vishalbarfiwala@gmail.com'], capture_output=True)
subprocess.run(['git', 'add', '-A'], capture_output=True)
subprocess.run(['git', 'commit', '-m', 'feat: autonomous alpha engine v1'], capture_output=True)

# Push via URL with token
remote_url = f'https://oauth2:{token}@github.com/medha-jarvis/autonomous-alpha-engine.git'
subprocess.run(['git', 'remote', 'add', 'origin', remote_url], capture_output=True)
result = subprocess.run(['git', 'push', '-u', 'origin', 'main'], capture_output=True, text=True, timeout=60)
print(f"Push stdout: {result.stdout[-500:]}")
print(f"Push stderr: {result.stderr[-500:]}")
print(f"Push returncode: {result.returncode}")
if result.returncode == 0:
    print("\n✅ GitHub repo ready!")
else:
    print("\n❌ Push failed")