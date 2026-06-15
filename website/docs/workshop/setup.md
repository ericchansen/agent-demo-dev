---
sidebar_position: 2
title: Setup Guide
---

# Setup Guide

Everything you need to run the two-day workshop: local development, Azure deployment, one data platform
connection, and the first quota report.

## Two-day setup checkpoints

| When | Outcome | Pages you'll use |
|---|---|---|
| **Day 1 morning** | Repo cloned, Python environment ready, Copilot CLI can see local MCP servers. | This page, [CLI Surface](../architecture/cli-surface) |
| **Day 1 afternoon** | Fabric Data Agent or Databricks Genie returns sales rows and the quota estimator writes XLSX/HTML/PDF. | [Choose Your Data Platform](../building-blocks/choose-data-platform), [Quota Pipeline](../building-blocks/quota-pipeline) |
| **Day 2 morning** | Foundry project contains visible agents and the playground can test the same workflow. | [Foundry Surface](../architecture/foundry-surface), [Azure AI Foundry](../building-blocks/foundry) |
| **Day 2 afternoon** | Agent is ready to publish to M365 Copilot, customize for your data, add skills, and trace runs. | [Ship It](../journey/ship-it) |

## Quick Start (CLI Surface)

### 1. Clone and install

<details>
<summary><strong>Option A: uv (recommended)</strong></summary>

[uv](https://docs.astral.sh/uv/) manages Python versions and virtual environments automatically.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

git clone https://github.com/ericchansen/agent-demo-dev.git
cd agent-demo-dev
uv sync --extra dev
```

> 📖 [uv documentation](https://docs.astral.sh/uv/)

</details>

<details>
<summary><strong>Option B: pip + venv</strong></summary>

```bash
git clone https://github.com/ericchansen/agent-demo-dev.git
cd agent-demo-dev
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -e ".[dev]"
```

</details>

### 2. Install GitHub Copilot CLI

```bash
# If you have GitHub CLI:
gh extension install github/gh-copilot

# Or install standalone:
# See https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers
```

> 📖 [Add MCP servers to GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)

### 3. Choose and connect a data platform

Use **one** of the two supported workshop data backends. The quota estimator normalizes both into the same
row contract (`territory`, `category`, `order_date`, `revenue`, `quantity`), so the later report and Foundry
steps do not change.

| Platform | Best when | Setup page |
|---|---|---|
| Microsoft Fabric Data Agent | You want the Microsoft-native Lakehouse and MCP path. | [Fabric Data Agent](../building-blocks/fabric-data-agent) |
| Databricks Genie + Unity Catalog | Your customer data already lives in Azure Databricks. | [Databricks Genie](../building-blocks/databricks-genie) |

#### Fabric MCP example

Edit `.github/mcp.json` with your Fabric workspace ID:

```json
{
  "mcpServers": {
    "wwi-sales-data": {
      "type": "http",
      "url": "api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"
    }
  }
}
```

Or use the CLI:

```bash
copilot mcp add --transport http wwi-sales-data \
  "api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"
```

> 📖 [MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) · [Fabric Data Agent MCP](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-mcp-server)

#### Databricks Genie example

Create a Genie Space over Unity Catalog sales tables, then call the Genie Spaces API from your data-agent adapter
or paste exported rows into the quota tool. The normalized rows can use Databricks-friendly aliases:

```json
{
  "sales_territory": "Northwest",
  "productCategory": "Novelty Items",
  "orderDate": "2026-05-05",
  "net_sales_amount": 260000,
  "units_sold": 520,
  "source_platform": "databricks"
}
```

> 📖 [Genie Spaces](https://learn.microsoft.com/en-us/azure/databricks/genie/) · [Genie Spaces API](https://learn.microsoft.com/en-us/azure/databricks/genie/conversation-api) · [Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)

### 4. Verify it works

```bash
copilot
> What were Tailspin Toys' total sales last quarter?
```

You should get a table of sales data from the Lakehouse or Genie Space. Then generate the first report:

```powershell
uv run python -c "from src.agents.quota_estimator.pipeline import demo_research_data, demo_sales_rows, demo_workiq_activity, generate_quota_estimation_report; print(generate_quota_estimation_report(customer_name='Tailspin Toys', sales_rows=demo_sales_rows(), research_data=demo_research_data('Tailspin Toys'), workiq_activity=demo_workiq_activity('Tailspin Toys'), output_dir='output/day1-first-report'))"
```

## Fabric Workspace Setup

### Create a Fabric workspace

1. Go to [app.fabric.microsoft.com](https://app.fabric.microsoft.com)
2. Create a new workspace
3. Enable Fabric capacity (F2 minimum for Data Agent)
4. Create a Lakehouse and load the WWI sample data

> 📖 [Create a Fabric workspace](https://learn.microsoft.com/fabric/get-started/create-workspaces) · [Fabric trial](https://learn.microsoft.com/fabric/get-started/fabric-trial)

### Configure the Data Agent

1. In your Fabric workspace, create a new Data Agent
2. Connect it to your Lakehouse tables
3. Add the instructions from `fabric/data-agent-instructions.md`
4. Optionally add few-shot examples from `fabric/few-shot-examples.json`

> 📖 [Create a Data Agent](https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent)

### Get your workspace ID

Your workspace ID is the GUID in the Fabric URL:
```
https://app.fabric.microsoft.com/groups/YOUR-WORKSPACE-ID/...
```

## Azure deployment and Foundry setup

Deploy the dev infrastructure after reviewing the what-if output:

```powershell
az deployment group what-if -g rg-fabric-agent-dev -f infra/main.bicep -p infra/parameters/dev.bicepparam
az deployment group create -g rg-fabric-agent-dev -f infra/main.bicep -p infra/parameters/dev.bicepparam
```

The dev parameter file sets `publicNetworkAccess = 'Enabled'` so the Foundry portal and hosted runtime are
reachable during the workshop. The Foundry project is created under the existing hub with:

```powershell
az ml workspace create --kind Project --hub-id "/subscriptions/9450bd3b-96c5-48b2-bfdf-3374304efbd7/resourceGroups/rg-fabric-agent-dev/providers/Microsoft.MachineLearningServices/workspaces/fabric-agent-hub-dev" --name fsa-project-dev --resource-group rg-fabric-agent-dev --location eastus2
```

See [Foundry Surface](../architecture/foundry-surface) for portal testing and [Ship It](../journey/ship-it)
for publishing. It covers:

- Foundry project creation
- Tool registration (FabricIQ, WorkIQ)
- Agent configuration and testing
- Publishing to M365

## Pause & Resume (Cost Management)

Fabric capacity billing runs continuously. **Pause when not demoing:**

```bash
# Pause (stops billing)
az fabric capacity suspend \
  --resource-group rg-fabric-agent \
  --capacity-name fabricagentdemo

# Resume (~1-2 min startup)
az fabric capacity resume \
  --resource-group rg-fabric-agent \
  --capacity-name fabricagentdemo
```

See [Cost Model](./costs) for full pricing details.
