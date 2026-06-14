# Setup Guide

End-to-end instructions for deploying the Fabric Sales Agent Accelerator, loading sample data, and running your first query.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Azure subscription** | With permissions to create resource groups and deploy Fabric capacity |
| **Microsoft Fabric** | F2 or higher capacity (F2 is sufficient for demos; pause when not in use) |
| **Python** | 3.11 or later |
| **Azure CLI** | `az` — [install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **Node.js** | 18+ — required for MCP tooling and VS Code Copilot extensions |
| **M365 Copilot license** | Required only if publishing to the M365 Copilot surface |
| **Git** | For cloning the repo |

---

## Step 1: Deploy Infrastructure

Deploy the Azure resources (Fabric capacity, resource group, Entra app registrations) using the provided Bicep templates.

```bash
# Login to Azure
az login

# Deploy all infrastructure
make infra-deploy
```

This runs `az deployment group create` with `infra/main.bicep` and the `infra/parameters/dev.bicepparam` parameter file. You can override the resource group and capacity name:

```bash
make infra-deploy RG=my-rg CAPACITY_NAME=my-capacity
```

For manual deployment or customization, see [infra/README.md](../infra/README.md).

---

## Step 2: Load Sample Data

Load the **Wide World Importers** sample dataset into your Fabric Lakehouse. This dataset represents a wholesale novelty goods distributor with customers, orders, products, and sales pipeline data.

```bash
make load-data
```

This script downloads WWI Parquet files from a public Azure Blob Storage container and uploads them into your Lakehouse. No customer-specific or sensitive data is used.

### Step 2b: Load Market Data (Optional)

To enable the **real-world market data path** alongside WWI, load SEC EDGAR financial data for ~50 major US public companies:

```bash
make load-market-data
```

This downloads a recent SEC EDGAR quarterly data set, filters to a curated company list (`demo/market-data/companies.csv`), normalizes US GAAP tags into simple columns (revenue, net_income, total_assets), and outputs Parquet + CSV files.

Then upload to a **separate** Fabric Lakehouse:

1. Create a new Lakehouse (e.g., `MarketDataLH`) in your workspace.
2. Upload `company_financials.parquet` and `companies.csv` from `demo/market-data/output/`.
3. Right-click each file → **Load to table**.

See [Data Paths](data-paths.md) for the full comparison of both data paths.

---

## Step 3: Create Fabric Data Agent

Create the Data Agent in the Fabric portal:

1. Open your **Fabric workspace** in the browser.
2. Click **+ New item** → select **Data Agent** (preview).
3. Name it (e.g., `Sales Agent`).
4. **Add a data source** → select the Lakehouse you loaded in Step 2.
5. **Configure the agent** using the instructions in `fabric/data-agent-config.json`:
   - Copy the data-source instructions from `fabric/data-source-instructions/` into the agent's instruction field.
   - Add example queries from `fabric/example-queries/` to improve NL→SQL accuracy.
6. **Publish** the agent.

---

## Step 4: Enable MCP Server

After publishing the Data Agent:

1. Open the published agent in the Fabric portal.
2. Go to **Settings** → **MCP** tab.
3. Toggle the MCP server **on**.
4. **Copy the MCP URL** — you'll need it in the next step.
5. **Download `mcp.json`** — this contains the server configuration for your IDE.

---

## Step 5: Configure CLI

Merge the Fabric MCP server config with the sub-agent configs for your VS Code / CLI environment.

1. Open `src/cli/mcp-config.json` — this contains the Researcher and SharePoint MCP server definitions.
2. Add the Fabric Data Agent MCP entry (from the `mcp.json` you downloaded in Step 4) to your VS Code MCP config:
   - **VS Code**: Settings → search "MCP" → edit `mcp.json`
   - **GitHub Copilot CLI**: `~/.copilot/mcp-config.json`
3. Set the required environment variables:

```bash
# Search provider for the Researcher Agent (bing, tavily, or mock)
export SEARCH_PROVIDER=mock

# SharePoint mode (live or mock)
export SHAREPOINT_MODE=mock

# Optional: Azure OpenAI endpoint (if not using Foundry-managed)
# export AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
```

For a real deployment, set `SEARCH_PROVIDER=bing` (with a Bing Search API key) or `SEARCH_PROVIDER=tavily` and `SHAREPOINT_MODE=live`.

---

## Step 6: Start Sub-Agents

Start the Researcher and SharePoint MCP servers. Each runs in its own terminal.

```bash
# Terminal 1 — Researcher Agent
make serve-researcher

# Terminal 2 — SharePoint Agent
make serve-sharepoint
```

Both servers start on stdio transport by default and will be discovered by your MCP client (VS Code, CLI).

---

## Step 7: Test

### Quick Smoke Test

Open **VS Code Copilot Chat** (or the GitHub Copilot CLI) and try:

> "What are our top 10 customers by revenue?"

The Fabric Data Agent should query OneLake and return results.

### Unit Tests

```bash
make test
```

### Eval Tests (with mock data)

```bash
make test-eval --mock
```

The eval suite runs predefined queries against mock sub-agents and checks that responses meet quality thresholds.

---

## Step 8 (Optional): Publish to M365

To make the agent available to business users in M365 Copilot Chat or Teams:

- **Zero-code path (Fabric data only):** Publish the Fabric Data Agent directly from the Fabric portal. See [docs/surfaces/m365-direct.md](surfaces/m365-direct.md) for step-by-step instructions.
- **Full workflow (data + research + reports):** Deploy the orchestrator via Azure AI Foundry and publish to M365. See [docs/surfaces/foundry.md](surfaces/foundry.md) for the pro-code path.
- **Low-code path (multi-source, no reports):** Build a Copilot Studio agent with Fabric, SharePoint, and web connectors. See [docs/surfaces/copilot-studio.md](surfaces/copilot-studio.md).

---

## Teardown

To avoid ongoing costs, **pause** the Fabric capacity when you're not using it:

```bash
make infra-teardown
```

This prints the `az fabric capacity suspend` command. Pausing stops billing for the Fabric capacity while preserving all data and configuration. Resume anytime from the Azure portal or CLI.
