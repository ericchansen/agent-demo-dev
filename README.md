# Fabric Sales Agent Accelerator

> 📖 **[Full documentation](https://ericchansen.github.io/agent-demo-dev/)** — architecture, demo script, setup guide, costs

## What it is

An AI sales agent accelerator for **Wide World Importers** that shows how to pair pluggable sales-data backends with two delivery surfaces: a fast developer prototype in GitHub Copilot CLI and a production path into **M365 Copilot + Teams**.

## The Two-Surface Approach

- **Surface 1: GitHub Copilot CLI** — prototype quickly with MCP servers for Fabric or Databricks data, M365 activity context, and inline report generation.
- **Surface 2: M365 Copilot + Teams** — graduate the same business flow into a registered Azure AI Foundry agent and publish it to Microsoft 365 Copilot and Teams.
- **WorkIQ note:** production uses WorkIQ for M365 activity context; the demo tenant uses a mock WorkIQ tool with sample activity data until tenant provisioning is available.

## Architecture diagram

```text
┌─ CLI Surface (Prototype) ─────────────────────┐
│ Copilot CLI → MCP Servers                      │
│   → wwi-sales-data (Fabric Data Agent)         │
│   → databricks_query (Genie / Unity Catalog)   │
│   → market-data (SEC EDGAR financials)         │
│   → workiq (M365 activity data)                │
│   → quota-forecast skill (inline report)       │
└────────────────────────────────────────────────┘

┌─ M365 Surface (Production) ───────────────────┐
│ M365 Copilot / Teams → Foundry Agent           │
│   → Fabric IQ — wwi_sales_data (WWI)           │
│   → Databricks Genie — databricks_query        │
│   → Fabric IQ — real_world_market_data (SEC)   │
│   → WorkIQ (M365 activity platform tool, OBO)  │
│   → Report Generator (DOCX + OneDrive link)    │
└────────────────────────────────────────────────┘

Same quota/reporting logic. Different data backends and distribution.
Data paths: Microsoft Fabric, Databricks Genie / Unity Catalog, and real-world SEC EDGAR enrichment.
```

## Quick Start (CLI)

```bash
git clone https://github.com/ericchansen/agent-demo-dev.git && cd agent-demo-dev
uv sync --extra dev              # or: python -m venv .venv && pip install -e ".[dev]"
```

Edit `.github/mcp.json` — replace `<your-workspace-id>` with your Fabric workspace GUID. Then:

```bash
copilot
# > What were Tailspin Toys' total sales last quarter?
```

See the [full setup guide](https://ericchansen.github.io/agent-demo-dev/docs/workshop/setup) for all options (uv, pip+venv, `copilot mcp add`, Fabric, Databricks, and Foundry).

## Pre-demo validation

Before presenting, run the full readiness path:

```bash
python scripts/predemo.py
```

Add `--azure` to include live dev Azure reachability checks and `--docker` to build and smoke-test the hosted-agent container.

## Tech Stack

- **Microsoft Fabric** — Data Agent and OneLake analytics
- **Azure Databricks** — Genie Spaces and Unity Catalog
- **Azure AI Foundry** — production agent for M365 Copilot and Teams
- **Model Context Protocol (MCP)** — tool surface for the CLI prototype
- **Python 3.11+** — agent, tool, and report-generation implementation

## Cost

Plan for roughly **~$270/month active** for the demo footprint. Pause Fabric capacity when idle to drop to roughly **~$15/month** in residual costs. See [docs/costs.md](docs/costs.md).

## Repository Structure

| Path | Purpose |
|------|---------|
| `src/cli/` | GitHub Copilot CLI prototype surface: MCP config and skills |
| `src/orchestrator/` | Azure AI Foundry agent for the M365 Copilot + Teams surface |
| `src/agents/` | Local MCP servers, demo mocks, and report generation helpers |
| `fabric/` | Fabric Data Agent instructions and example queries |
| `infra/` | Bicep infrastructure for Fabric and Azure resources |
| `demo/` | Wide World Importers sample assets and demo content |
| `docs/` | Setup, architecture, cost, and two-surface guidance |
| `docs/surfaces/` | Reference-only alternatives such as Copilot Studio and M365 Direct Publish |
| `tests/` | Unit and integration coverage |

## License

[MIT](LICENSE)
