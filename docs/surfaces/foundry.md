# Surface: Azure AI Foundry (Pro-Code)

> **Full orchestration via Python SDK.** Use FabricIQPreviewTool for data queries, optional WorkIQPreviewTool for activity context, and custom functions for quota forecasting and report generation — then publish to M365 Copilot or Teams.

**Citation:** <https://learn.microsoft.com/en-us/fabric/data-science/data-agent-foundry>

---

## How It Works

Azure AI Foundry provides a Python SDK (`azure-ai-projects`) that lets you build a fully customizable agent with function calling. You register tools — including Fabric's built-in `FabricIQPreviewTool` for NL→SQL, optional `WorkIQPreviewTool` for M365 activity context, and your own custom functions for everything else — and the LLM orchestrates which tools to call based on the user's question.

```
User → M365 Copilot Chat / Teams / Custom UI
  → Azure AI Foundry Agent
    → FabricIQPreviewTool → Fabric Lakehouse SQL
    → WorkIQPreviewTool / get_account_activity() → M365 engagement signals
    → forecast_quota() → local projection logic
    → generate_report() → python-docx / python-pptx → file output
  → Combined multi-source answer + attachments
```

This is the most powerful surface — and the most complex. You get full control over orchestration, tool selection, error handling, and output formatting.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Azure subscription** | For the AI Services account, Foundry project, and model deployments |
| **Azure AI Services account + project** | Created via Azure portal or `az cognitiveservices account project create` |
| **Model deployment** | GPT-4o or equivalent deployed in your Foundry project |
| **Fabric capacity** | F2 or higher (for the Fabric Data Agent / FabricIQPreviewTool) |
| **Fabric Data Agent** | Must already exist — used as the `FabricIQPreviewTool` data source |
| **M365 Copilot license** | Required for end users if publishing to M365 Copilot Chat or using WorkIQ |
| **Python environment** | 3.11+ with `azure-ai-projects` |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│  Azure AI Foundry Project                    │
│                                              │
│  ┌─────────────┐   ┌──────────────────────┐  │
│  │  LLM Agent  │──▶│  Tool Registry       │  │
│  │  (GPT-4o)   │   │                      │  │
│  └─────────────┘   │  • FabricIQPreviewTool │  │
│                     │  • WorkIQPreviewTool  │  │
│                     │  • forecast_quota     │  │
│                     │  • generate_report    │  │
│                     └──────────────────────┘  │
│                                              │
│  ┌─────────────────────────────────────────┐  │
│  │  Agent Version + Responses API         │  │
│  │  create_version → responses.create     │  │
│  └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   Fabric Lakehouse      External APIs
   (SQL queries)         (Web, SharePoint, etc.)
```

---

## Capabilities

| Capability | Supported |
|---|---|
| Natural-language → SQL queries (via FabricIQPreviewTool) | ✅ |
| M365 activity grounding (via WorkIQPreviewTool) | ✅ |
| Quota forecasting (local function) | ✅ |
| Report generation (DOCX) | ✅ (custom function) |
| Custom function calling | ✅ |
| Multi-agent orchestration | ✅ |
| M365 Copilot Chat | ✅ (via publish) |
| Teams | ✅ (via Bot Framework or publish) |
| Custom web UI | ✅ |
| CLI interface | ✅ |
| Full Python control | ✅ |
| Version-controlled pipeline | ✅ |

---

## Key Components

### FabricIQPreviewTool

The SDK provides a built-in `FabricIQPreviewTool` that wraps your Fabric Data Agent. Register it with the agent and it handles NL→SQL translation automatically.

```python
from azure.ai.projects.models import FabricIQPreviewTool

fabric_tool = FabricIQPreviewTool(
    project_connection_id="your-fabric-iq-connection-id",
    require_approval="never",
)
```

### Custom Functions

Define Python functions that the LLM can call. Each function receives a `dict` of arguments and returns a `dict` of results.

| Function | Purpose |
|---|---|
| `get_account_activity` | Mock M365 activity fallback when WorkIQ isn't configured |
| `forecast_quota` | Generate an FY quota projection from trailing sales trends |
| `generate_report` | Create DOCX reports from collected data |

### Agent Creation

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FabricIQPreviewTool, FunctionTool, PromptAgentDefinition

agent = project_client.agents.create_version(
    agent_name="WWISalesAgent",
    definition=PromptAgentDefinition(
        model=model_deployment_name,
        instructions="You are a sales analyst for Wide World Importers...",
        tools=[fabric_tool, function_tool],
    ),
)
```

### Response Flow

```python
response = openai_client.responses.create(
    input=question,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
```

---

## Limitations

| Limitation | Impact |
|---|---|
| **Requires Python development** | Not suitable for no-code/low-code teams |
| **More infrastructure** | Azure subscription, AI Services account, model deployments |
| **Deployment complexity** | Must manage agent lifecycle, versioning, and monitoring |
| **Cost** | Azure OpenAI token costs + Fabric capacity + infrastructure |
| **Preview APIs** | Agent versioning and Fabric/WorkIQ preview tools may change before GA |

---

## When to Use This Surface

✅ **Use when:**
- You need the full pipeline: Fabric sales queries + activity context + quota forecasting + report generation.
- You want custom orchestration logic (retry, fallback, conditional tool selection).
- You need to generate downloadable files (DOCX, PPTX).
- You're building a production-grade agent with version-controlled code.
- You want to expose the agent to M365 Copilot, Teams, CLI, and custom UIs simultaneously.

❌ **Don't use when:**
- You only need simple Fabric data queries (use [M365 Direct Publish](m365-direct.md)).
- You want a low-code setup without Python (use [Copilot Studio](copilot-studio.md)).
- You're just doing a quick demo with no custom tools needed.

---

## Reference Implementation

This repo provides working Foundry agents at two tiers:

### Prompt Agent (Declarative)
- [`foundry_agent.py`](../../src/orchestrator/foundry_agent.py) — Agent creation, tool registration, and run loop
- [`config.py`](../../src/orchestrator/config.py) — Environment-based configuration
- Tools: `FabricIQPreviewTool`, `web_research`, `compute_quota_attainment`, `forecast_quota`, `generate_report`, `get_account_activity`

### Hosted Agent (Copilot SDK-compatible runtime)
- [`hosted_agent/__init__.py`](../../src/orchestrator/hosted_agent/__init__.py) — Hosted runtime with injectable chat adapter, local demo flow, tool definitions, and handlers
- [`hosted_agent/server.py`](../../src/orchestrator/hosted_agent/server.py) — HTTP invocation server for Foundry managed runtime
- [`hosted_agent/Dockerfile`](../../src/orchestrator/hosted_agent/Dockerfile) — Container definition

The Hosted Agent is a bring-your-own-code container. It exposes an injectable chat adapter for Copilot SDK integration and a deterministic local demo runtime, so the same container can be smoke-tested without live model credentials. It wires the full tool set: `fabric_query`, `forecast_quota`, `generate_quota_estimation_report`, `generate_report`, `web_research`, `compute_quota_attainment`, and `get_account_activity`.

Hosted runtime configuration:

| Variable | Purpose |
|---|---|
| `FABRIC_MCP_URL` | Fabric Data Agent MCP endpoint used by `fabric_query` |
| `FABRIC_MCP_TOOL_NAME` | MCP tool name to call, for example the Fabric Data Agent query tool exposed by the endpoint |
| `MODEL_ENDPOINT` | Optional model/Copilot SDK endpoint used by an injected hosted chat adapter |
| `MODEL_DEPLOYMENT` | Model deployment name, defaulting to `gpt-4o` |
| `HOSTED_AGENT_OUTPUT_DIR` | Local artifact directory for hosted quota reports, defaulting to `output/hosted-agent` |
| `COPILOT_HOME` | Optional credential/cache location if the selected Copilot SDK adapter requires it |

Any additional Copilot SDK auth/runtime variables are adapter-specific and should be supplied through the Foundry container environment, not committed to source.

### Scale-Up Path: Microsoft Agent Framework (MAF)

For scenarios requiring **multi-agent orchestration** (e.g., separate agents for data gathering, analysis, and report generation that coordinate via a supervisor), consider [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) (`pip install microsoft-agent-framework`). MAF provides:

- **Multi-agent patterns**: Supervisor, sequential, parallel agent topologies
- **Stateful conversations**: Agent memory and context management
- **Built-in tool protocols**: MCP and OpenAPI tool integration
- **Observability**: Tracing and debugging across agent boundaries

MAF is the right choice when a single agent with tools becomes unwieldy — typically when you need 3+ specialized agents that hand off work. For this accelerator's current scope (one agent with multiple tools), the Copilot SDK approach is simpler and sufficient.

See the root [README](../../README.md) for setup instructions.
