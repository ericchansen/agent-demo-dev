# Demo 2 — Full Workflow (15 minutes)

> **Audience:** Technical decision-makers, data/AI engineers
> **Goal:** Show the complete workflow — internal data + external research → cited report
> **Surfaces:** Copilot CLI + M365 Copilot + Foundry Portal

---

## Prerequisites

| Requirement | Details |
|---|---|
| Fabric capacity | F2 or higher, **active** |
| Fabric Data Agent | Published as **SalesAgent** |
| Market Research service | Running (see [market-research repo](https://github.com/ericchansen/market-research)) |
| CLI configured | `src/cli/mcp-config.json` with `sales-data` server registered |
| GitHub Copilot CLI | Installed in VS Code or terminal |
| M365 Copilot license | For showing the M365 surface |
| Foundry project | `fsa-foundry-project-dev` with SalesAgent registered |

### Pre-flight checklist (15 min before)

- [ ] Verify Fabric capacity is active
- [ ] Open terminal at repo root — run `make test` to confirm environment works
- [ ] Open VS Code with Copilot CLI active
- [ ] Open [M365 Copilot Chat](https://m365.cloud.microsoft/chat) in a browser tab
- [ ] Open [Foundry Portal](https://ai.azure.com) in another tab
- [ ] Have a sample XLSX pre-generated as fallback

---

## Part 1 — CLI Prototype Surface (5 minutes)

### 1. Set the scene

> **Say:**
> "As engineers, we prototype in the terminal. Copilot CLI gives us MCP servers that connect to the same Fabric Data Agent, plus external services. Let me show the developer experience."

### 2. Query sales data

**In Copilot CLI, type:**
`What's our pipeline coverage ratio for the Northwest territory?`

> **Point out:** "This hits the `sales-data` MCP server, which proxies to Fabric Data Agent. Same data, same governance — just a different surface."

### 3. Add market context

**Type:**
`Now get me recent SEC filings and market data for our top 3 customers there`

> **Point out:** "This calls the market-research service — a separate deployment that pulls SEC EDGAR data and financial APIs. Internal + external data, one conversation."

### 4. Generate a report

**Type:**
`Generate a quota estimation report for Northwest with conservative and aggressive scenarios`

> **Point out:** "The `quota-forecast` skill synthesizes both data sources, runs scenario modeling, and produces an Excel workbook with methodology citations."

---

## Part 2 — Foundry Portal (3 minutes)

### 5. Show agent registration

- Open Azure AI Foundry → navigate to the project
- Show the **SalesAgent** in the agents list
- Open the playground, run a test query

> **Say:**
> "Same agent, same instructions, now running as a managed Foundry agent. We can trace every tool call, inspect latency, and monitor usage."

### 6. Show traces

- Navigate to **Tracing** in the Foundry portal
- Show a recent trace with tool calls

---

## Part 3 — M365 Production Surface (4 minutes)

### 7. Switch to M365 Copilot

- Open M365 Copilot Chat
- **@SalesAgent** — run the same pipeline coverage question

> **Say:**
> "One workflow, three surfaces. The CLI for prototyping, Foundry for testing and monitoring, M365 for the end users. Same data governance throughout."

### 8. Show the architecture slide

> **Point out the 5-surface diagram** from `docs/diagrams/architecture.md`

---

## Wrap up (1 minute)

> **Say:**
> "What you just saw is a single workflow — query internal data, enrich with external research, produce cited artifacts — delivered through three surfaces today and extensible to Copilot Studio and Teams. The code is open source, the data stays governed, and you can start with just the CLI prototype and graduate to production when ready."