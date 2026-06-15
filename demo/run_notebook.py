"""Update Fabric notebook with wasbs:// fix and run it."""

import base64
import json
import os
import shutil
import subprocess
import time

import requests

AZ = os.environ.get("AZ_CLI") or shutil.which("az") or shutil.which("az.cmd") or "az"


def get_token():
    return (
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
NB = os.environ.get("FABRIC_NOTEBOOK_ID", "01353aa2-9eae-415b-87f7-6d22a1cfa578")
LH = os.environ.get("FABRIC_LAKEHOUSE_ID", "94178450-6f04-44a5-9a54-eabfbe6ea292")

code_lines = [
    'blob_base = "wasbs://sampledata@fabrictutorialdata.blob.core.windows.net/WideWorldImportersDW/csv/full"\n',
    "tables = ["
    '"dimension_city", "dimension_customer", "dimension_date", '
    '"dimension_employee", "dimension_stock_item", "fact_sale"]\n',
    "for table in tables:\n",
    '    print(f"Loading {table}...")\n',
    '    df = spark.read.option("header", "true").option("inferSchema", "true").csv(f"{blob_base}/{table}/")\n',
    '    df.write.mode("overwrite").format("delta").saveAsTable(table)\n',
    "    count = spark.table(table).count()\n",
    '    print(f"  {table}: {count} rows loaded")\n',
    'print("All tables loaded!")',
]

ipynb = json.dumps(
    {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "language_info": {"name": "python"},
            "trident": {
                "lakehouse": {
                    "known_lakehouses": [{"id": LH}],
                    "default_lakehouse": LH,
                    "default_lakehouse_name": "wwi_lakehouse",
                    "default_lakehouse_workspace_id": WS,
                }
            },
        },
        "cells": [{"cell_type": "code", "source": code_lines, "metadata": {}, "outputs": []}],
    }
)

b64 = base64.b64encode(ipynb.encode()).decode()
body = {
    "definition": {
        "format": "ipynb",
        "parts": [{"path": "notebook-content.py", "payload": b64, "payloadType": "InlineBase64"}],
    }
}

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Step 1: Update definition
print("Updating notebook definition...")
r = requests.post(
    f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{NB}/updateDefinition", headers=headers, json=body
)
print(f"Update: {r.status_code}")
loc = r.headers.get("Location", "")

# Step 2: Poll update
for i in range(12):
    time.sleep(5)
    pr = requests.get(loc, headers={"Authorization": f"Bearer {token}"}).json()
    status = pr.get("status", "?")
    print(f"  {(i + 1) * 5}s: {status}")
    if status in ("Succeeded", "Failed"):
        break

if status != "Succeeded":
    print(f"FAILED: {pr.get('error', {}).get('message', pr)}")
    exit(1)

# Step 3: Run notebook
print("Running notebook...")
time.sleep(3)
rr = requests.post(
    f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{NB}/jobs/instances?jobType=RunNotebook",
    headers=headers,
)
print(f"Run submitted: {rr.status_code}")
run_loc = rr.headers.get("Location", "")

# Step 4: Poll run
for i in range(30):
    time.sleep(30)
    t = get_token()
    sr = requests.get(run_loc, headers={"Authorization": f"Bearer {t}"}).json()
    s = sr.get("status", "?")
    print(f"  {(i + 1) * 30}s: {s}")
    if s in ("Completed", "Failed", "Cancelled"):
        if s == "Failed":
            print(f"  Error: {sr.get('failureReason', {}).get('message', 'unknown')}")
        break

print(f"\nFINAL: {sr.get('status')}")
