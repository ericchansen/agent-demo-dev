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

This accelerator supports five architecture options for exposing the agent to end users:

| Surface | Description | Status |
|---------|-------------|--------|
| **GitHub Copilot CLI** | Full multi-agent workflow via MCP tool calls in your terminal. Skill-based orchestration chains Fabric, research, and WorkIQ into artifacts (Excel, HTML, DOCX). | ✅ Implemented |
| **M365 Copilot (Direct Publish)** | Zero-code path — publish from Fabric portal directly into M365 Copilot Chat | ✅ Implemented |
| **Azure AI Foundry (Prompt Agent)** | Declarative agent with FunctionTools for quota forecasting, web research, attainment computation, and DOCX report generation | ✅ Implemented |
| **Azure AI Foundry (Hosted Agent)** | Bring-your-own-code container with Fabric MCP, quota, research, attainment, activity, and report tools | ✅ Implemented |
| **Cowork** | M365 plugin surface with native WorkIQ access. Maps 1:1 to CLI skill pattern. | 📋 Documented |

See [docs/surfaces/README.md](surfaces/README.md) for a detailed comparison and decision flowchart.

---

## Data Flow

1. **User request** — A user asks a natural language question (e.g., "Run a deep analysis for Tailspin Toys") through any consumption surface.
2. **Orchestrator** — The orchestrator (CLI skill, Foundry Prompt Agent, or Hosted Agent) decomposes the request into sub-tasks.
3. **Parallel data gathering** — The orchestrator invokes data sources in parallel:
   - **Fabric Data Agent** → queries revenue, pipeline, and customer data from OneLake
   - **Web Research** → searches for market trends, customer news, competitive intelligence
   - **WorkIQ / M365 Activity** → retrieves engagement signals (meetings, emails, contacts)
4. **Computation** — Derived metrics are computed: quota attainment, pipeline coverage, run rate projection, risk rating, relationship strength.
5. **Synthesis** — All gathered and computed data is assembled into a **JSON intermediate format** (`schemas/sales-analysis-output.json`) that serves as the single input for all artifact generators.
6. **Artifact generation** — Based on the requested format:
   - **Excel** → `src/cli/report-scripts/sales-report-generator.cjs` (multi-tab workbook via ExcelJS)
   - **HTML** → `src/cli/report-scripts/dashboard-template.html` (Chart.js interactive dashboard)
   - **DOCX** → `src/agents/report_generator/` (python-docx with charts and citations)
   - **Markdown** → Inline in chat response
7. **Response** — The final answer (executive summary + artifact link) is returned to the user.

---

## Authentication Model

The system uses three authentication modes depending on the runtime context:

| Mode | When Used | Details |
|------|-----------|---------|
| **Interactive delegated (Entra ID)** | CLI and VS Code users | User signs in; tokens flow to sub-agents via on-behalf-of |
| **Cross-tenant proxy** | CLI accessing remote Fabric tenant | `src/cli/fabric_mcp_proxy.py` acquires tokens via `az CLI` for the target subscription |
| **Managed identity** | Azure AI Foundry runtime | System-assigned MI authenticates to Fabric, Graph, and Azure OpenAI |
| **OIDC federated credential** | GitHub Actions CI/CD | Workload identity federation — no stored secrets |

See [docs/security-model.md](security-model.md) for the full security model including authorization, data protection, and governance.

---

> **Note:** See `docs/diagrams/` for visual architecture diagrams.
