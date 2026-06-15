"""Publish the Fabric Data Agent."""

import os
import shutil
import subprocess

import requests

AZ = os.environ.get("AZ_CLI") or shutil.which("az") or shutil.which("az.cmd") or "az"
token = (
    subprocess.check_output(
        [
            AZ,
            "account",
            "get-access-token",
            "--resource",
            "https://api.fabric.microsoft.com",
            "--query",
            "accessToken",
            "--output",
            "tsv",
        ]
    )
    .decode()
    .strip()
)

WS = os.environ.get("FABRIC_WORKSPACE_ID", "6cf857b8-a0d0-4029-af88-62a83b4116e5")
AGENT = os.environ.get("FABRIC_DATA_AGENT_ID", "f89ca52e-8d23-4020-b0ab-489ab57d0d14")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

endpoints = [
    (
        "PublishDataAgent job",
        f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{AGENT}/jobs/instances?jobType=PublishDataAgent",
    ),
    ("dataAgents publish", f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/dataAgents/{AGENT}/publish"),
    ("items publish", f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{AGENT}/publish"),
]

for name, url in endpoints:
    r = requests.post(url, headers=headers)
    status = "submitted" if r.status_code == 202 else r.text[:300]
    print(f"{name}: {r.status_code} — {status}")
    if r.status_code == 202:
        loc = r.headers.get("Location", "none")
        print(f"  Location: {loc}")
        break
