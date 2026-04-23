# Surface: Azure AI Foundry (Pro-Code)

> **Full orchestration via Python SDK.** Use FabricTool for data queries, custom functions for web research, SharePoint search, and report generation — then publish to M365 Copilot or Teams.

**Citation:** <https://learn.microsoft.com/en-us/fabric/data-science/data-agent-foundry>

---

## How It Works

Azure AI Foundry provides a Python SDK (`azure-ai-agents`, `azure-ai-projects`) that lets you build a fully customizable agent with function calling. You register tools — including Fabric's built-in `FabricTool` for NL→SQL and your own custom functions for everything else — and the LLM orchestrates which tools to call based on the user's question.

```
User → M365 Copilot Chat / Teams / Custom UI
  → Azure AI Foundry Agent
    → FabricTool → Fabric Lakehouse SQL
    → research_customer() → Bing/Tavily web search
    → search_sharepoint() → SharePoint/Graph API
    → generate_report() → python-docx / python-pptx → file output
  → Combined multi-source answer + attachments
```

This is the most powerful surface — and the most complex. You get full control over orchestration, tool selection, error handling, and output formatting.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Azure subscription** | For Foundry hub, project, and model deployments |
| **Azure AI Foundry hub + project** | Created via Azure portal or `az` CLI |
| **Model deployment** | GPT-4o or equivalent deployed in your Foundry project |
| **Fabric capacity** | F2 or higher (for the Fabric Data Agent / FabricTool) |
| **Fabric Data Agent** | Must already exist — used as the `FabricTool` data source |
| **M365 Copilot license** | Required for end users if publishing to M365 Copilot Chat |
| **Python environment** | 3.10+ with `azure-ai-agents`, `azure-ai-projects` |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│  Azure AI Foundry Project                    │
│                                              │
│  ┌─────────────┐   ┌──────────────────────┐  │
│  │  LLM Agent  │──▶│  Tool Registry       │  │
│  │  (GPT-4o)   │   │                      │  │
│  └─────────────┘   │  • FabricTool         │  │
│                     │  • research_customer  │  │
│                     │  • search_sharepoint  │  │
│                     │  • generate_report    │  │
│                     └──────────────────────┘  │
│                                              │
│  ┌─────────────────────────────────────────┐  │
│  │  Thread / Run Loop                      │  │
│  │  create thread → send msg → poll → done │  │
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
| Natural-language → SQL queries (via FabricTool) | ✅ |
| Web research (Bing, Tavily, or custom) | ✅ (custom function) |
| SharePoint search (Graph API) | ✅ (custom function) |
| Report generation (DOCX, PPTX) | ✅ (custom function) |
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

### FabricTool

The SDK provides a built-in `FabricTool` that wraps your Fabric Data Agent. Register it with the agent and it handles NL→SQL translation automatically.

```python
from azure.ai.agents.models import FabricTool

fabric_tool = FabricTool(
    fabric_connection_id="your-fabric-connection-id"
)
```

### Custom Functions

Define Python functions that the LLM can call. Each function receives a `dict` of arguments and returns a `dict` of results.

| Function | Purpose |
|---|---|
| `research_customer` | Web search for customer/competitor intelligence |
| `search_sharepoint` | Query SharePoint via Graph API for internal docs |
| `generate_report` | Create DOCX/PPTX reports from collected data |

### Agent Creation

```python
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FunctionTool, FabricTool

agent = project_client.agents.create_agent(
    model=model_deployment_name,
    name="WWI Sales Agent",
    instructions="You are a sales analyst for Wide World Importers...",
    tools=[fabric_tool, function_tool],
)
```

### Run Loop

```python
thread = project_client.agents.threads.create()
project_client.agents.messages.create(thread_id=thread.id, role="user", content=question)
run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
messages = project_client.agents.messages.list(thread_id=thread.id)
```

---

## Limitations

| Limitation | Impact |
|---|---|
| **Requires Python development** | Not suitable for no-code/low-code teams |
| **More infrastructure** | Azure subscription, Foundry hub, model deployments |
| **Deployment complexity** | Must manage agent lifecycle, versioning, and monitoring |
| **Cost** | Azure OpenAI token costs + Fabric capacity + infrastructure |
| **Preview APIs** | `azure-ai-agents` SDK is in preview — breaking changes possible |

---

## When to Use This Surface

✅ **Use when:**
- You need the full pipeline: data queries + web research + SharePoint + report generation.
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

This repo provides a working Foundry orchestrator in `src/orchestrator/`:

- [`foundry_agent.py`](../../src/orchestrator/foundry_agent.py) — Agent creation, tool registration, and run loop
- [`config.py`](../../src/orchestrator/config.py) — Environment-based configuration

See the root [README](../../README.md) for setup instructions.
