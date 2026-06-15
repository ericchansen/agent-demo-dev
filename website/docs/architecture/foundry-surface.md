---
sidebar_position: 3
title: Foundry Surface
---

# Foundry Surface Architecture

The Foundry surface publishes the agent as an Azure AI Foundry Agent Application, accessible through M365 Copilot Chat and Teams. This is the production deployment path for business users.

## Architecture

```mermaid
flowchart LR
    User["Business User"] --> M365["M365 Copilot Chat\nor Teams"]
    M365 --> App["Agent Application\n(Entra identity)"]
    App --> Foundry["Foundry Agent Service\n(Responses API)"]
    Foundry --> FIQ["FabricIQPreviewTool"]
    Foundry --> DBX["Databricks Genie\nfunction adapter"]
    Foundry --> WIQT["WorkIQPreviewTool"]
    Foundry --> Func["Report generator\n(function tool)"]
    FIQ --> DA["Fabric Data Agent"]
    DA --> LH["Lakehouse"]
    DBX --> UC["Unity Catalog"]
    WIQT --> Graph["M365 Graph\n(OBO)"]
    Func --> OD["OneDrive"]
```

## How it works

1. User @mentions the agent in M365 Copilot Chat or Teams
2. The Agent Application routes the request to the Foundry Agent Service
3. The Responses API matches intent to registered tools
4. Platform tools (FabricIQ, WorkIQ) handle data access with built-in auth
5. Custom function tools (report generator) execute business logic
6. Response is returned to the user with adaptive card formatting

## Project and portal experience

The dev hub is `fabric-agent-hub-dev` in `eastus2`. The workshop project is `fsa-project-dev` under that hub.

**Reproducible provisioning (preferred).** The project is declared in Bicep as a `kind: 'Project'`
workspace (`infra/modules/foundry-project.bicep`, wired into `infra/main.bicep` via the
`foundryProjectName` parameter). A full infra deploy therefore recreates the project, not just the hub:

```powershell
az deployment group create -g rg-fabric-agent-dev -f infra/main.bicep -p infra/parameters/dev.bicepparam
```

**Manual bootstrap (equivalent).** If you are provisioning the project by itself, the `az` command
below produces the same resource:

```powershell
az ml workspace create --kind Project --hub-id "/subscriptions/9450bd3b-96c5-48b2-bfdf-3374304efbd7/resourceGroups/rg-fabric-agent-dev/providers/Microsoft.MachineLearningServices/workspaces/fabric-agent-hub-dev" --name fsa-project-dev --resource-group rg-fabric-agent-dev --location eastus2
```

### Register the agent before you look for it in the portal

The portal only shows an agent **after** you register it from code. Agents are not created by the
infra deploy — they are created by the SDK path in `src/orchestrator/foundry_agent.py`. Register the
WWI single agent first:

```powershell
# Requires a model deployment and a Fabric IQ connection on the project (see Setup).
uv run python -m src.orchestrator "Generate a quota report for Tailspin Toys"
```

This calls `create_version` for the `WWISalesAgent` and then runs the query. Once it has run
successfully at least once, open the Foundry portal (`https://ai.azure.com`):

1. Open **fabric-agent-hub-dev** and select the **fsa-project-dev** project.
2. Open **Agents**. You should now see the `WWISalesAgent` registration. (If the list is empty, the
   registration step above has not completed — re-run it and check the CLI output for errors.)
3. Open the agent in **Playground** and run `Generate a quota report for Tailspin Toys`.
4. Open tracing or observability views and inspect the tool calls, latency, and generated artifact metadata.
5. Use **Publish** when the agent is ready for Microsoft 365 Copilot and Teams.

> **Prerequisites for live registration.** The project needs (a) a chat model deployment whose name
> matches `MODEL_DEPLOYMENT_NAME`, and (b) a Fabric IQ connection whose ID matches
> `FABRIC_IQ_CONNECTION_ID`. Without both, `create_version` / the Responses call will fail. See the
> [Setup guide](../workshop/setup.md) for wiring these connections.

## Multi-agent pipeline alternative

The single-agent path is simplest: one Foundry agent has Fabric/Databricks, WorkIQ, research, and report tools.
The advanced path decomposes the same business outcome:

```mermaid
flowchart LR
    User --> Conversation["Conversational Agent"]
    Conversation --> Planner["Planner Agent"]
    Planner --> Data["Data Agent\nFabric or Databricks"]
    Planner --> Research["Research Agent"]
    Planner --> Work["Work Context Agent"]
    Conversation --> Report["Report Agent"]
    Data --> Conversation
    Research --> Conversation
    Work --> Conversation
    Report --> Files["XLSX + HTML + PDF"]
```

Use the multi-agent pattern when you need independent observability, separate ownership, or agent-specific
evaluation. Use the single-agent pattern when speed, fewer registrations, and simpler publishing matter more.

> **Scope honesty.** The multi-agent pipeline shipped in this repo is a **local, deterministic proof of
> concept** (`src/orchestrator/multi_agent/`). It runs the planner → data → research → context → report
> stages in-process to mirror the single-agent output, so you can demo and unit-test the decomposition
> without provisioning six Foundry agents. It is **not** live Foundry agent-to-agent chaining yet: the
> stage names map to the `foundry_agent_name` slots that *would* be registered, but no inter-agent
> Foundry calls are made. Promote it to live chaining only after registering each stage as its own
> Foundry agent and validating SDK support — then add portal traces here. The working PoC is invocable with:

```powershell
uv run python -m src.orchestrator.multi_agent "Generate a quota report for Tailspin Toys" --customer "Tailspin Toys" --data-source fabric
uv run python -m src.orchestrator.multi_agent "Generate a quota report for Tailspin Toys" --customer "Tailspin Toys" --data-source databricks
```

## Key characteristics

| Aspect | Detail |
|---|---|
| **Orchestrator** | Foundry Responses API |
| **Tool protocol** | Foundry tool registration (platform + function tools) |
| **Auth** | OBO (on-behalf-of) via Entra |
| **Output** | Adaptive cards, DOCX links, rich formatting |
| **Infrastructure** | Azure AI Foundry (managed) |
| **Distribution** | M365 Copilot Chat, Teams, direct API |

## Components

| Component | Location | Purpose |
|---|---|---|
| Agent orchestrator | `src/orchestrator/` | Foundry agent configuration and tool wiring |
| Hosted agent runtime | `src/orchestrator/hosted_agent/` | Bring-your-own-code container with Fabric MCP, quota, research, attainment, activity, and report tools |
| Report generator | `src/agents/report_generator/` | DOCX generation + OneDrive upload |
| Infra (Bicep) | `infra/` | Foundry hub + project (`kind: 'Project'`), storage, Key Vault, Fabric capacity. Agents and Entra app are registered out-of-band (SDK / CLI). |

## Hosted runtime configuration

Set these environment variables on the hosted container:

| Variable | Purpose |
|---|---|
| `FABRIC_MCP_URL` | Fabric Data Agent MCP endpoint |
| `FABRIC_MCP_TOOL_NAME` | MCP tool name to invoke for natural-language Fabric questions |
| `MODEL_ENDPOINT` | Optional endpoint for an injected Copilot SDK-compatible chat adapter |
| `MODEL_DEPLOYMENT` | Model deployment name, defaulting to `gpt-4o` |
| `HOSTED_AGENT_OUTPUT_DIR` | Output directory for generated quota artifacts |
| `COPILOT_HOME` | Optional credential/cache path if your Copilot SDK adapter requires it |

## When to use the Foundry surface

- **Business users** — people who work in Teams and Outlook, not terminals
- **Enterprise distribution** — Entra identity, RBAC, compliance
- **Rich output** — DOCX reports, adaptive cards, OneDrive links
- **Production** — monitored, scalable, auditable

> 📖 [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) · [Publish agents to Microsoft 365 Copilot and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot) · [Tracing for AI agents](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup)
