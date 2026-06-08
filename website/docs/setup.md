---
sidebar_position: 5
title: Setup Guide
---

# Setup Guide

## Quick Start (CLI Surface)

### 1. Clone and install

<details>
<summary><strong>Option A: uv (recommended)</strong></summary>

[uv](https://docs.astral.sh/uv/) manages Python versions and virtual environments automatically -- no global installs, no manual venv activation.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
# or: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

# Clone and install
git clone https://github.com/ericchansen/agent-demo.git
cd agent-demo
uv sync --extra dev        # creates .venv, installs all deps + dev tools
```

Run commands with `uv run`:
```bash
uv run pytest tests/unit/
uv run python -m src.orchestrator
```

</details>

<details>
<summary><strong>Option B: pip + venv</strong></summary>

```bash
git clone https://github.com/ericchansen/agent-demo.git
cd agent-demo
python -m venv .venv

# Activate the virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Install
pip install -e ".[dev]"
```

</details>

### 2. Connect the Fabric Data Agent

The repo includes a workspace `.github/mcp.json` that Copilot CLI auto-discovers. You just need to set your Fabric workspace ID.

**Option A: Edit `.github/mcp.json`** (zero-config)

Open `.github/mcp.json` in the repo and replace `<your-workspace-id>` with your Fabric workspace GUID:

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

Copilot CLI loads this automatically when you run from the project directory.

**Option B: `copilot mcp add`** (one-liner, saved to your user config)

```bash
copilot mcp add --transport http wwi-sales-data \
  "https://api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"
```

**Option C: Inline for a single session**

```bash
copilot --additional-mcp-config '{"wwi-sales-data":{"type":"http","url":"https://api.fabric.microsoft.com/v1/mcp/workspaces/YOUR-WORKSPACE-ID/dataagent"}}'
```

### 3. Start asking questions

```bash
copilot
# > What were Tailspin Toys' total sales last quarter?
```

Copilot CLI authenticates to Fabric via OAuth -- you'll get a browser prompt on first use.

## Foundry Surface Setup

See the [full setup guide](https://github.com/ericchansen/agent-demo/blob/main/docs/setup-guide.md) for Azure AI Foundry configuration, Fabric IQ connections, and M365 publishing.
