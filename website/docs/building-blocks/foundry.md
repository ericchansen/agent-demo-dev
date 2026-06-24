---
sidebar_position: 4
title: Azure AI Foundry
---

# Azure AI Foundry

Azure AI Foundry is the production runtime for the agent in this accelerator. It provides agent orchestration, tool registration, identity management, and publishing to M365 Copilot and Teams. If the CLI surface is where you prototype, Foundry is where you deploy.

## Key concepts

### Agent Service
The Foundry Agent Service hosts your agent and manages its lifecycle. It handles:
- **Conversation management** — threads, message history, context windows
- **Tool orchestration** — routing user intent to registered tools
- **Response generation** — combining tool outputs into coherent answers

> 📖 [Agent Service overview](https://learn.microsoft.com/en-us/azure/foundry/agents/overview)

### Responses API
The Responses API is how the agent calls tools and generates responses. It supports:
- **Function calling** — the agent decides which tools to call based on user intent
- **Streaming** — progressive output for long-running operations
- **Structured output** — JSON responses for programmatic consumption

> 📖 [Microsoft Foundry SDKs and endpoints](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/sdk-overview)

### Platform tools vs function tools

| Type | Description | Example |
|---|---|---|
| **Platform tool** | First-party Microsoft tools with built-in auth | FabricIQPreviewTool, WorkIQPreviewTool |
| **Function tool** | Custom code you write and register | Report generator, forecast calculator |
| **Code interpreter** | Built-in Python sandbox for data analysis | Ad-hoc calculations, chart generation |

Platform tools handle authentication and data access automatically. Function tools give you full control over logic and output.

> 📖 [Function calling](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling) · [Code interpreter](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/code-interpreter)

### Published agents for Microsoft 365
A registered Foundry agent can be published to Microsoft 365 Copilot and Teams with:
- **Entra identity** — its own app registration for auth
- **Stable endpoint** — accessible from M365 Copilot, Teams, or direct API
- **RBAC** — control who can discover and use the agent
- **Monitoring** — usage metrics, error tracking, cost attribution

> 📖 [Publish agents to Microsoft 365 Copilot and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot) · [Agent tracing](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup)

## How it fits in this accelerator

The accelerator implements **two Foundry agent patterns**:

### Prompt Agent (declarative)
The primary production path (`src/orchestrator/foundry_agent.py`). Registers tools declaratively:

1. **FabricIQPreviewTool** — wraps the same Fabric Data Agent endpoint used by the CLI
2. **WorkIQPreviewTool** — wraps WorkIQ with OBO authentication
3. **Web research function** — searches for market intelligence and competitive data
4. **Attainment function** — computes quota attainment from Fabric data
5. **Report generator function** — produces DOCX/PPTX, uploads to OneDrive, returns download link

### Multi-agent workflow

The same `SalesAgent` is already a multi-step workflow: a single prompt agent that pulls **internal** data
(Fabric sales) and **external** data (SEC EDGAR financials for real US public companies, plus web research),
adds WorkIQ activity context, and calls quota + report functions to produce the deliverable. One agent,
many tools, one complex task — that is the pipeline.

Run it locally:

```powershell
uv run python -m src.orchestrator "Generate a quota report for Tailspin Toys"
```

When you need genuinely **separate sub-agents** with their own ownership and traces, two paths exist:

| Path | What it is | Where it lives |
|---|---|---|
| Databricks Supervisor Agent | A supervisor that fans out to specialist sub-agents over Unity Catalog data. | `src/orchestrator/databricks_supervisor.py` (configured in the Databricks UI / API). |
| Market Research agent | A separately deployed external research agent the workflow calls for deep market/competitive analysis. | [`ericchansen/market-research`](https://github.com/ericchansen/market-research) — its own repo and IaC. |

Both keep the orchestrating Sales Agent thin while pushing specialized work to a dedicated agent.

The live Fabric Data Agent path **has** been validated out-of-band against the dev workspace. A manual MCP smoke test (`initialize` → `tools/list` → `tools/call`) against the live Sales Data Agent tool returned real rows from the sample sales warehouse, confirming token acquisition for `api.fabric.microsoft.com`, the MCP endpoint, and natural-language query execution all work end to end; it is exercised manually because CI has no Fabric credentials.

The agent's system prompt encodes the orchestration logic — when to call which tool, how to combine results, and how to format output.

## CLI → Foundry translation

| What you did in CLI | How it maps to Foundry |
|---|---|
| Added an MCP server | Register a platform/function tool |
| Wrote a skill | Encode workflow in agent system prompt |
| Tested with `copilot` | Test in Foundry playground |
| Shared via `.github/mcp.json` | Publish the registered Foundry agent to Microsoft 365 |

The mental model: CLI is your workbench, Foundry is your factory.

## Further reading

- [Microsoft Foundry overview](https://learn.microsoft.com/en-us/azure/foundry/)
- [Agent Service overview](https://learn.microsoft.com/en-us/azure/foundry/agents/overview)
- [Function calling](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling)
- [Publishing to M365](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot)
- [Tracing agents](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup)
