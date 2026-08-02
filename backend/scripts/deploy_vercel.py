#!/usr/bin/env python3
"""Deploy frontend to Vercel via API."""
import json
import os
import sys
import urllib.error
import urllib.request


def get_token():
    """Extract Vercel token from .env or auth.json."""
    env_path = "/opt/data/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("VERCEL_TOKEN"):
                    eq_pos = stripped.index("=")
                    return stripped[eq_pos + 1:]

    auth_path = os.path.expanduser("~/.vercel/auth.json")
    if os.path.exists(auth_path):
        with open(auth_path) as f:
            auth = json.load(f)
            return auth.get("token", "")

    return ""


def main():
    token = get_token()
    if not token:
        print("ERROR: No Vercel token found")
        sys.exit(1)

    print(f"Token found: {token[:10]}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    project_name = "autonomous-alpha-engine"

    # Create/update project
    project_data = {
        "name": project_name,
        "framework": "nextjs",
        "gitRepository": {
            "repo": "medha-jarvis/autonomous-alpha-engine",
            "type": "github",
        },
        "environmentVariables": [
            {
                "key": "TYPESENSE_URL",
                "value": "http://31.97.227.135:8700",
                "target": "production",
            },
            {
                "key": "TYPESENSE_API_KEY",
                "value": "alpha-engine-api-proxy-2026",
                "target": "production",
            },
        ],
    }

    req = urllib.request.Request(
        "https://api.vercel.com/v9/projects",
        data=json.dumps(project_data).encode(),
        headers=headers,
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        proj = json.loads(resp.read())
        print(f"Project: {proj.get('name', 'OK')}")
        print(f"Project ID: {proj.get('id', '?')}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"Project error {e.code}")
        if e.code == 409:
            print("Project already exists — will deploy anyway")

    # Trigger deployment
    deploy_data = {
        "name": project_name,
        "project": project_name,
        "target": "production",
        "gitSource": {
            "type": "github",
            "ref": "main",
        },
    }

    req2 = urllib.request.Request(
        "https://api.vercel.com/v13/deployments",
        data=json.dumps(deploy_data).encode(),
        headers=headers,
    )
    try:
        resp2 = urllib.request.urlopen(req2, timeout=30)
        dep = json.loads(resp2.read())
        url = dep.get("url", "?")
        state = dep.get("readyState", "?")
        print(f"\nDeployment triggered!")
        print(f"URL: https://{url}")
        print(f"State: {state}")
        if state == "READY":
            print(f"Dashboard: https://{url}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"Deploy error {e.code}: {err[:300]}")
        print("\nManual deploy instructions:")
        print("1. Go to https://vercel.com/import/git")
        print("2. Import medha-jarvis/autonomous-alpha-engine")
        print("3. Root dir: frontend")
        print("4. Add env var TYPESENSE_URL=http://31.97.227.135:8700")
        print("5. Add env var TYPESENSE_API_KEY=alpha-engine-api-proxy-2026")
        print("6. Deploy")


if __name__ == "__main__":
    main()