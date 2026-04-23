# Agent Instructions (AGENTS.md)

## Project Overview

**Fabric Sales Agent Accelerator** is an open-source reference implementation demonstrating how to combine Microsoft Fabric Data Agent with agentic AI workflows. It uses the Wide World Importers sample dataset (wholesale novelty goods).

## Architecture

Four sub-agents orchestrated by a pluggable front-end:

1. **Fabric Data Agent** — NL→SQL/DAX/KQL queries over OneLake data (built-in MCP server)
2. **Researcher Agent** — Web search for customer intelligence (custom MCP server)
3. **SharePoint Agent** — Internal doc retrieval via Graph API (custom MCP server)
4. **Report Generator** — Template-based DOCX/PPTX generation with citations

Four consumption surfaces (all demonstrated, none "picked"):
- GitHub Copilot (VS Code / CLI) via MCP
- M365 Copilot via direct Agent Store publish
- Copilot Studio via connected agent
- Azure AI Foundry via Python SDK + M365 publish

## Coding Standards

- **Language:** Python 3.11+
- **Linting:** Ruff (rules: E, F, I, N, W, UP). Line length 120.
- **Type checking:** mypy strict for `src/agents/`, lenient for integration code
- **Testing:** pytest. Unit tests mock external services. Integration tests verify MCP protocol.
- **Formatting:** Ruff formatter
- **IaC:** Bicep (Azure-native). Modules in `infra/modules/`.
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `infra:`, `test:`)

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | Sub-agent MCP servers and report generator |
| `src/orchestrator/` | Azure AI Foundry orchestrator agent |
| `src/cli/skills/` | Copilot CLI skill definitions |
| `infra/` | Bicep IaC (Fabric capacity, Key Vault, Entra app, Foundry) |
| `fabric/` | Fabric Data Agent config, instructions, few-shot examples |
| `demo/` | Sample data (WWI), SharePoint demo docs, demo scripts |
| `docs/` | Architecture, security, setup, surfaces comparison |
| `tests/` | Unit, integration, and eval tests |

## Important Notes

- **LLM-agnostic** — never hardcode a model provider. Config accepts any endpoint.
- **Citations first-class** — every generated report must include source attribution.
- **Fabric MCP is built-in** — use the Data Agent's native MCP server, not a custom wrapper.
- **Auth split** — interactive for CLI, managed identity for Foundry, OIDC for CI, bot reg for M365.
- **No customer data in repo** — all data is Wide World Importers (Microsoft sample).
