---
sidebar_position: 2
title: Setup Guide
---

# Setup Guide

Everything you need to run this workshop — from local development to Fabric workspace configuration.

## Quick Start (CLI Surface)

### 1. Clone and install

<details>
<summary><strong>Option A: uv (recommended)</strong></summary>

[uv](https://docs.astral.sh/uv/) manages Python versions and virtual environments automatically.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

git clone https://github.com/ericchansen/agent-demo.git
cd agent-demo
uv sync --extra dev
```

> 📖 [uv documentation](https://docs.astral.sh/uv/)

</details>

<details>
<summary><strong>Option B: pip + venv</strong></summary>

```bash
git clone https://github.com/ericchansen/agent-demo.git
cd agent-demo
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
# See https://docs.github.com/copilot/github-copilot-in-the-cli/installing-copilot-cli
```

> 📖 [Copilot CLI installation](https://docs.github.com/copilot/github-copilot-in-the-cli/installing-copilot-cli)

### 3. Connect the Fabric Data Agent

Edit `.github/mcp.json` with your Fabric workspace ID:

```json
{
  "mcpServers": {
    "wwi-sales-data": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"
    }
  }
}
```

Or use the CLI:

```bash
copilot mcp add --transport http wwi-sales-data \
  "https://api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"
```

> 📖 [MCP configuration](https://docs.github.com/copilot/github-copilot-in-the-cli/using-mcp-servers-with-copilot-cli) · [Fabric Data Agent MCP](https://learn.microsoft.com/fabric/data-engineering/data-agent-mcp)

### 4. Verify it works

```bash
copilot
> What were Tailspin Toys' total sales last quarter?
```

You should get a table of sales data from the Lakehouse.

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

> 📖 [Create a Data Agent](https://learn.microsoft.com/fabric/data-engineering/data-agent-create)

### Get your workspace ID

Your workspace ID is the GUID in the Fabric URL:
```
https://app.fabric.microsoft.com/groups/YOUR-WORKSPACE-ID/...
```

## Foundry Surface Setup

For Azure AI Foundry configuration, see the [full setup guide](https://github.com/ericchansen/agent-demo/blob/main/docs/setup-guide.md) in the repo. It covers:

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
