"""Configure the Fabric Data Agent with lakehouse data source and instructions."""

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
AGENT = os.environ.get("FABRIC_DATA_AGENT_ID", "f89ca52e-8d23-4020-b0ab-489ab57d0d14")
LH = os.environ.get("FABRIC_LAKEHOUSE_ID", "94178450-6f04-44a5-9a54-eabfbe6ea292")

data_agent_json = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataAgent/2.1.0/schema.json",
    "dataSources": [
        {
            "type": "Lakehouse",
            "workspaceId": WS,
            "artifactId": LH,
            "displayName": "wwi_lakehouse",
            "description": "sales sales data",
        }
    ],
}

instructions = """\
You are an AI assistant for sales, a wholesale novelty goods distributor.
Help sales users query their pipeline, analyze customer trends, and prepare account plans.

## Data Sources
- fact_sale: Sales transactions with customer, stock item, quantity, unit price,
  total including tax, profit, invoice date
- dimension_customer: Customer details including name, category, buying group, city
- dimension_stock_item: Product catalog with item name, color, size, brand, category
- dimension_city: Geographic data - city, state/province, country, continent, sales territory
- dimension_employee: Salespeople and their details
- dimension_date: Date dimension for time-based analysis

## Key Terminology
- Buying Group: Customer classification (e.g., Tailspin Toys, Wingtip Toys)
- Stock Category: Product type classification
- Sales Territory: Geographic sales region

## Response Guidelines
- Use tables for multi-row results
- Include totals where appropriate
- Round currency values to 2 decimal places
- When asked about top customers, order by Total Including Tax descending"""

stage_config_json = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/stageConfiguration/1.0.0/schema.json",
    "aiInstructions": instructions,
}

platform_json = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {
        "type": "DataAgent",
        "displayName": "Sales Agent",
        "description": (
            "AI assistant for sales. Queries sales pipeline, customer data, product catalog, and territory information."
        ),
    },
    "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
}

parts = [
    {
        "path": "Files/Config/data_agent.json",
        "payload": base64.b64encode(json.dumps(data_agent_json).encode()).decode(),
        "payloadType": "InlineBase64",
    },
    {
        "path": "Files/Config/draft/stage_config.json",
        "payload": base64.b64encode(json.dumps(stage_config_json).encode()).decode(),
        "payloadType": "InlineBase64",
    },
    {
        "path": ".platform",
        "payload": base64.b64encode(json.dumps(platform_json).encode()).decode(),
        "payloadType": "InlineBase64",
    },
]

body = {"definition": {"parts": parts}}

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("Updating Data Agent definition...")
r = requests.post(
    f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{AGENT}/updateDefinition", headers=headers, json=body
)
print(f"Status: {r.status_code}")
loc = r.headers.get("Location", "")

for i in range(12):
    time.sleep(5)
    pr = requests.get(loc, headers={"Authorization": f"Bearer {token}"}).json()
    s = pr.get("status", "?")
    print(f"  {(i + 1) * 5}s: {s}")
    if s in ("Succeeded", "Failed"):
        if s == "Failed":
            err = pr.get("error", {})
            print(f"  Error: {err.get('message', err)}")
        break

print(f"\nDONE: {s}")
print(
    f"\nAgent URL: https://app.powerbi.com/groups/{WS}/dataagent/{AGENT}?ctid=9c74def4-ef0a-418a-8dc7-1e7a1e85ce10&experience=fabric-developer"
)
