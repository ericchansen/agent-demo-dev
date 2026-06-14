#!/usr/bin/env python3
"""Configure a Fabric Data Agent for the market-data demo path.

Parameterized version of configure_agent.py — accepts workspace, agent,
and lakehouse IDs as CLI arguments instead of hardcoded values.

Usage:
    python demo/configure_market_agent.py \\
        --workspace-id <GUID> \\
        --agent-id <GUID> \\
        --lakehouse-id <GUID>
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import time

import requests


def _find_az() -> str:
    """Locate the Azure CLI executable on PATH."""
    for name in ("az", "az.cmd"):
        path = shutil.which(name)
        if path:
            return path
    msg = "Azure CLI not found on PATH. Install from https://aka.ms/installazurecli"
    raise FileNotFoundError(msg)


AZ = _find_az()


def get_token() -> str:
    """Get a Fabric API access token via Azure CLI."""
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


INSTRUCTIONS = """\
You are an AI assistant for market research and competitive intelligence.
You have access to SEC EDGAR financial data for major US public companies.
Help users query company financials, compare competitors, and analyze industry trends.

## Data Sources
- company_financials: Normalized quarterly financial data from SEC 10-K and 10-Q filings.
  Columns: cik, ticker, company_name, sic_code, industry, form, fiscal_year,
  fiscal_period, period_end_date, filed, revenue, net_income, total_assets
- companies: Company profiles with ticker symbols, SIC industry codes, and sector labels.
  Columns: cik, ticker, company_name, sic_code, industry

## Key Terminology
- CIK: Central Index Key — SEC's unique company identifier
- SIC: Standard Industrial Classification — industry categorization code
- 10-K: Annual financial filing
- 10-Q: Quarterly financial filing
- Fiscal Period: FY = full year, Q1-Q3 = quarters

## Response Guidelines
- Always cite the data source (SEC EDGAR) and filing period
- Use tables for multi-row results
- Round currency values to millions (e.g., $45,123M) for readability
- When comparing companies, sort by the primary metric descending
- If a company has no data for a requested metric, say so explicitly
- Join company_financials to companies on cik for industry/sector context
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure a Fabric Data Agent for market data.",
    )
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace GUID")
    parser.add_argument("--agent-id", required=True, help="Fabric Data Agent item GUID")
    parser.add_argument("--lakehouse-id", required=True, help="Fabric Lakehouse item GUID")
    args = parser.parse_args()

    ws = args.workspace_id
    agent = args.agent_id
    lh = args.lakehouse_id

    data_agent_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/dataAgent/2.1.0/schema.json",
        "dataSources": [
            {
                "type": "Lakehouse",
                "workspaceId": ws,
                "artifactId": lh,
                "displayName": "market_data_lakehouse",
                "description": "SEC EDGAR financial data and company profiles",
            }
        ],
    }

    stage_config_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/definition/stageConfiguration/1.0.0/schema.json",
        "aiInstructions": INSTRUCTIONS,
    }

    platform_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "DataAgent",
            "displayName": "Market Data Agent",
            "description": (
                "AI assistant for market research. Queries SEC EDGAR financials, "
                "company profiles, and industry data for major US public companies."
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

    print("Updating Market Data Agent definition...")
    r = requests.post(
        f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/items/{agent}/updateDefinition",
        headers=headers,
        json=body,
    )
    r.raise_for_status()
    print(f"Status: {r.status_code}")
    loc = r.headers.get("Location", "")
    if not loc:
        print("No Location header — update may have completed synchronously.")
        return

    s = "Unknown"
    for i in range(12):
        time.sleep(5)
        poll = requests.get(loc, headers={"Authorization": f"Bearer {token}"})
        poll.raise_for_status()
        pr = poll.json()
        s = pr.get("status", "?")
        print(f"  {(i + 1) * 5}s: {s}")
        if s in ("Succeeded", "Failed"):
            if s == "Failed":
                err = pr.get("error", {})
                print(f"  Error: {err.get('message', err)}")
            break

    if s != "Succeeded":
        raise SystemExit(f"Agent update failed with status: {s}")

    print(f"\nDONE: {s}")


if __name__ == "__main__":
    main()
