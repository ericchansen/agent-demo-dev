# Agent Instructions (AGENTS.md)

## Project Overview

**Fabric Sales Agent Accelerator** is an open-source reference implementation demonstrating how to combine Microsoft Fabric Data Agent with agentic AI workflows. It uses the Wide World Importers sample dataset (wholesale novelty goods).

## Architecture

This demo is scoped to **two delivery surfaces** that share the same WWI sales scenario and Fabric backend:

1. **GitHub Copilot CLI (prototype)** — MCP-based developer surface
   - `wwi-sales-data` for Fabric Data Agent queries
   - `workiq` for M365 activity context (**mocked in the demo tenant**)
   - `quota-forecast` skill for inline report output
2. **M365 Copilot + Teams (production path)** — Azure AI Foundry agent published via Agent Application
   - `FabricIQPreviewTool` for Fabric-backed NL→SQL
   - `WorkIQPreviewTool` for M365 activity data in production
   - Custom function tools for report generation and business actions

**Copilot Studio** and **M365 Direct Publish** are documented in `docs/surfaces/` but not implemented in this demo.

## Coding Standards

- **Language:** Python 3.11+
- **Linting:** Ruff (rules: E, F, I, N, W, UP). Line length 120.
- **Type checking:** mypy strict for `src/agents/`, lenient for integration code
- **Testing:** pytest. Unit tests mock external services. Integration tests verify MCP protocol.
- **Formatting:** Ruff formatter
- **IaC:** Bicep (Azure-native). Modules in `infra/modules/`.
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `infra:`, `test:`)

## CI Checks

CI runs on every PR to `main`. Run these locally before pushing:

```bash
pip install -r requirements.txt            # runtime deps
pip install ruff mypy pytest pytest-asyncio # dev tools
ruff check .                               # lint
ruff format --check .                      # formatting (run `ruff format .` to auto-fix)
mypy src/                                  # type checking
pytest tests/unit/                         # unit tests
```

All four must pass. The Bicep template is also validated (`az bicep build --file infra/main.bicep`).

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | Local MCP servers, demo mocks, and report generation helpers |
| `src/orchestrator/` | Azure AI Foundry agent and tool wiring for the M365 / Teams surface |
| `src/cli/` | Copilot CLI MCP config and skills for the prototype surface |
| `infra/` | Bicep IaC (Fabric capacity, Key Vault, Entra app, Foundry) |
| `fabric/` | Fabric Data Agent config, instructions, few-shot examples |
| `demo/` | Sample data (WWI) and demo assets |
| `docs/` | Architecture, security, setup, and two-surface guidance |
| `docs/surfaces/` | Reference-only documentation for additional surfaces |
| `tests/` | Unit, integration, and eval tests |

## Important Notes

- **LLM-agnostic** — never hardcode a model provider. Config accepts any endpoint.
- **Citations first-class** — every generated report must include source attribution.
- **Fabric MCP is built-in** — use the Data Agent's native MCP server, not a custom wrapper.
- **Auth split** — interactive for CLI, managed identity for Foundry, OIDC for CI, bot reg for M365.
- **WorkIQ demo mode** — production targets WorkIQ / OBO flows; the demo tenant uses mock M365 activity data until provisioning is available.
- **No customer data in repo** — all data is Wide World Importers (Microsoft sample).
