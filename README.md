# Sales Agent Demo

> 📖 **[Full documentation](https://ericchansen.github.io/agent-demo-dev/)** — architecture, demo scripts, setup guide, costs

## What it is

A sales intelligence workflow demo showing how to build an AI agent that pulls internal sales data + external market research + M365 activity context → synthesizes → produces actionable artifacts (XLSX/HTML/PDF reports).

Delivered across **5 surfaces** — same workflow, different topologies:

| Surface | Topology | Status |
|---------|----------|--------|
| **Copilot CLI** | MCP servers + skills | ✅ Working |
| **M365 Copilot** | Foundry agent card | ✅ Working |
| **Teams** | Foundry agent card | ✅ Working |
| **Copilot Studio** | Low-code topics | 📄 Documented |
| **Foundry Portal** | Playground | ✅ Working |

See [`docs/diagrams/architecture.md`](docs/diagrams/architecture.md) for the full architecture diagram.

## Quick Start (CLI)

```bash
git clone https://github.com/ericchansen/agent-demo-dev.git && cd agent-demo-dev
uv sync --extra dev              # or: python -m venv .venv && pip install -e ".[dev]"
```

Edit `.github/mcp.json` — replace `<WORKSPACE_ID>` and `<DATA_AGENT_ID>` with your Fabric workspace GUID. Then:

```bash
copilot
# > What were Microsoft's total sales last quarter?
# > Generate a quota estimation report for Northwest territory
```

See the [full setup guide](https://ericchansen.github.io/agent-demo-dev/docs/workshop/setup) for all options.

## Pre-demo validation

```bash
python scripts/predemo.py         # basic readiness checks
python scripts/predemo.py --azure # include live Azure reachability
```

## Tech Stack

- **Microsoft Fabric** — Data Agent and OneLake analytics
- **Azure Databricks** — Genie Spaces and Unity Catalog (alternative backend)
- **Azure AI Foundry** — production agent for M365 Copilot and Teams
- **Model Context Protocol (MCP)** — tool surface for the CLI prototype
- **Python 3.11+** — agent, tool, and report-generation implementation

## Data Sources

- **Internal**: Sales transactions, pipeline, territory data (Fabric lakehouse or Databricks)
- **External**: SEC EDGAR financials for ~50 US public companies (via separate [`market-research`](https://github.com/ericchansen/market-research) repo)
- **Activity**: M365 signals via WorkIQ (mocked in demo tenant)

## Cost

~$270/month active. Pause Fabric capacity when idle → ~$15/month residual. See [docs/costs.md](docs/costs.md).

## Repository Structure

| Path | Purpose |
|------|---------|
| `src/cli/` | Copilot CLI surface: MCP config and skills |
| `src/orchestrator/` | Azure AI Foundry agent (M365/Teams/Foundry surfaces) |
| `src/agents/` | Local MCP servers, demo mocks, report generation |
| `fabric/` | Fabric Data Agent instructions and example queries |
| `infra/` | Bicep IaC for Fabric and Azure resources |
| `demo/` | Demo scripts and sample data |
| `docs/` | Architecture, setup, costs, surface guides |
| `tests/` | Unit and integration tests |

## License

[MIT](LICENSE)
