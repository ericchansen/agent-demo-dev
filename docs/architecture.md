# Architecture Overview

This repo provides a **Fabric Sales Agent Accelerator** — a reference implementation that combines a Microsoft Fabric Data Agent with purpose-built sub-agents for sales workflows. A natural language request triggers parallel data retrieval from Fabric OneLake, web research, and internal SharePoint documents, then synthesizes the results into a cited deliverable (DOCX or PPTX). The system can be surfaced through four architecture options ranging from zero-code to full pro-code orchestration.

---

## System Components

### Fabric Data Agent

The core data layer. Fabric Data Agent exposes a **built-in MCP server** that translates natural language questions into SQL queries against Fabric OneLake (Lakehouse). It is **read-only** — no writes to the lakehouse are permitted — and enforces **row-level security** so users only see data they are authorized to access. The agent is configured via `fabric/data-agent-config.json`, which specifies lakehouse sources, data-source instructions, and example queries that improve NL→SQL accuracy.

### Researcher Agent

A **custom MCP server** (`src/agents/researcher/`) that performs web research on behalf of the user. It accepts a search query and returns summarized results with source URLs. The search provider is **configurable** (Bing, Tavily, or mock) via the `SEARCH_PROVIDER` environment variable, making it easy to swap providers or use a mock during testing. Only the search query text is sent externally — no internal data leaves the system.

### SharePoint Agent

A **custom MCP server** (`src/agents/sharepoint/`) that retrieves internal documents from SharePoint Online via the Microsoft Graph API. It can search for documents by keyword, retrieve file content, and list items in specific libraries. The agent respects SharePoint's native permission model — site, library, and item-level permissions are enforced by Graph API, so users only see documents they already have access to. Configurable via `SHAREPOINT_MODE` (live or mock).

### Report Generator

A report generation module that produces **DOCX and PPTX deliverables** from Jinja2-based templates. Every generated report includes full **source citations** — data source identifiers, web URLs, and timestamps — so the reader can trace every claim back to its origin. Templates live in `src/orchestrator/templates/` and are customizable per organization.

---

## Consumption Surfaces

This accelerator supports four architecture options for exposing the agent to end users:

| Surface | Description |
|---------|-------------|
| **GitHub Copilot (VS Code / CLI)** | Full multi-agent workflow via MCP tool calls in your editor or terminal |
| **M365 Copilot (Direct Publish)** | Zero-code path — publish from Fabric portal directly into M365 Copilot Chat |
| **Copilot Studio** | Low-code visual designer with connectors for Fabric, SharePoint, and web search |
| **Azure AI Foundry** | Pro-code Python SDK with full orchestration, report generation, and M365 publish |

See [docs/surfaces/README.md](surfaces/README.md) for a detailed comparison and decision flowchart.

---

## Data Flow

1. **User request** — A user asks a natural language question (e.g., "Prepare an account plan for Tailspin Toys") through any consumption surface.
2. **Orchestrator** — The orchestrator (CLI agent, Foundry agent, or Copilot Studio flow) decomposes the request into sub-tasks.
3. **Parallel sub-agent calls** — The orchestrator invokes sub-agents in parallel:
   - **Fabric Data Agent** → queries pipeline/revenue data from OneLake
   - **Researcher Agent** → searches the web for customer news, earnings, strategy
   - **SharePoint Agent** → retrieves internal proposals, playbooks, prior QBR decks
4. **Synthesis** — The orchestrator combines all sub-agent results into a coherent narrative with citations.
5. **Report generation** — If a deliverable is requested, the Report Generator renders a DOCX or PPTX from templates, embedding all citations and data.
6. **Response** — The final answer (text + optional report attachment) is returned to the user.

---

## Authentication Model

The system uses three authentication modes depending on the runtime context:

| Mode | When Used | Details |
|------|-----------|---------|
| **Interactive delegated (Entra ID)** | CLI and VS Code users | User signs in; tokens flow to sub-agents via on-behalf-of |
| **Managed identity** | Azure AI Foundry runtime | System-assigned MI authenticates to Fabric, Graph, and Azure OpenAI |
| **OIDC federated credential** | GitHub Actions CI/CD | Workload identity federation — no stored secrets |

See [docs/security-model.md](security-model.md) for the full security model including authorization, data protection, and governance.

---

> **Note:** See `docs/diagrams/` for visual architecture diagrams.
