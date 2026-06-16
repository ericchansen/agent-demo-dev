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

### Hosted Agent (bring-your-own-code)
A containerized agent (`src/orchestrator/hosted_agent/`) with full control over tool orchestration. It exposes a `HostedChatAdapter` chat surface plus a deterministic local demo flow, and it wires the same production tool set: Fabric MCP queries, quota forecasting, quota estimation artifacts, report generation, web research, quota attainment, and account activity fallback.

### Multi-agent pipeline (advanced)

The advanced lab registers separate Foundry-facing agent responsibilities:

| Agent | Responsibility | Local proof-of-concept equivalent |
|---|---|---|
| Planner | Decide which specialist agents are needed. | `MultiAgentPipeline.run(...)` |
| Data | Query Fabric Data Agent or Databricks Genie. | `_demo_data_agent(...)` |
| Research | Gather market and competitive context. | `web_research_func(...)` |
| Work Context | Add WorkIQ or synthetic M365 activity. | `mock_workiq_func(...)` |
| Conversational | Synthesize and interact with the user. | `MultiAgentPipelineResult.response` |
| Report | Generate XLSX/HTML/PDF quota artifacts. | `generate_quota_estimation_report_func(...)` |

Run it locally before registering agents in Foundry:

```powershell
uv run python -m src.orchestrator.multi_agent "Generate a quota report for Tailspin Toys" --customer "Tailspin Toys" --data-source databricks
```

:::note[Which runtime actually runs?]

The `WWI_MULTI_AGENT_RUNTIME` switch (or `--runtime`) selects how the pipeline executes:

| Runtime | Default? | What it is |
|---|---|---|
| `deterministic` | ✅ Yes | A fully **offline** pipeline that mirrors the single-agent quota flow with fixed routing — **no model call, no Azure credentials**. It produces identical artifacts every run, which is what CI and offline demos exercise. |
| `agent-framework` | No | The **live** Microsoft Agent Framework path (`agent-framework` extra). Requires a Foundry project endpoint, a model deployment, and `DefaultAzureCredential`; this is the only mode that actually invokes a model. |

The deterministic default is intentional for reproducible demos — do not read a green
CI run as proof that the live Agent Framework orchestration ran. Set
`WWI_MULTI_AGENT_RUNTIME=agent-framework` with Azure configured to exercise the real path.
:::

#### Adapter modes

`process_invocation()` resolves a chat adapter through `build_adapter()`, selected by the `HOSTED_AGENT_ADAPTER` environment variable:

| Mode | Adapter | When to use |
|---|---|---|
| `auto` (default) | Azure if configured, else local runtime | Safe default — uses the model only when `MODEL_ENDPOINT` and `MODEL_DEPLOYMENT` are set, otherwise the deterministic local runtime |
| `local` | `LocalDeterministicAdapter` | Offline demos and tests — routes each prompt to one tool and drives the real tool-calling loop with no credentials |
| `azure` | `AzureManagedIdentityChatAdapter` | Production — authenticates with `DefaultAzureCredential` (the container's managed identity) and calls the Foundry project's chat-completions deployment |

#### Configuration

Configure hosted containers with `FABRIC_MCP_URL`, `FABRIC_MCP_TOOL_NAME`, `MODEL_ENDPOINT` (Foundry project endpoint), and `MODEL_DEPLOYMENT` (model deployment name). Set `HOSTED_AGENT_ADAPTER` to pick the adapter mode and `HOSTED_AGENT_OUTPUT_DIR` when you want quota artifacts written outside the default `output/hosted-agent` path. The `azure` adapter raises a clear `HostedAgentConfigurationError` listing any missing variables.

Each tool call emits a structured, content-free log line (`tool=… status=… duration_ms=… artifacts=…`) so tool routing, latency, and failures are observable without leaking customer data or generated report content.

#### Validation status

The deterministic local adapter, factory selection, and tool routing are covered by offline unit tests and the `python scripts/demo_check.py --docker` smoke check. The `azure` adapter is unit-tested against a mocked model client; live model validation is **not** exercised in CI and requires a real `MODEL_ENDPOINT` and managed-identity credentials.

The live Fabric Data Agent path **has** been validated out-of-band against the dev workspace. A manual MCP smoke test (`initialize` → `tools/list` → `tools/call`) against the `DataAgent_WWI_Sales_Agent` tool returned real Wide World Importers results — for example, "top 3 customers by total sales" resolved to Wingtip Toys (~$712M) and Tailspin Toys (~$605M) over the WWI warehouse. This confirms token acquisition for `api.fabric.microsoft.com`, the MCP endpoint, and natural-language query execution all work end to end; it is exercised manually because CI has no Fabric credentials.

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
