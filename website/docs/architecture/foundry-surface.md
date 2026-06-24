---
sidebar_position: 3
title: Foundry Surface
---

# Foundry Surface Architecture

:::info[Where you are · 🗓️ Day 2]

The Foundry surface is where **Day 2** begins: you take the same agent workflow from Day 1
and ship it as a registered Azure AI Foundry agent, test it in the Playground, then publish
to M365 Copilot and Teams. See the [Workshop Overview](../intro) for the full path.
:::

The Foundry surface registers the agent in Azure AI Foundry, then publishes that agent to M365 Copilot Chat and Teams. This is the production deployment path for business users.

## Architecture

```mermaid
flowchart LR
    User["Business User"] --> M365["M365 Copilot Chat\nor Teams"]
    M365 --> Published["Published Foundry agent\n(Entra identity + RBAC)"]
    Published --> Foundry["Foundry Agent Service\n(Responses API)"]
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
2. The published Foundry agent routes the request to the Foundry Agent Service
3. The Responses API matches intent to registered tools
4. Platform tools (FabricIQ, WorkIQ) handle data access with built-in auth
5. Custom function tools (report generator) execute business logic
6. Response is returned to the user with adaptive card formatting

## Project and portal experience

This repo uses the **modern (account-based)** Foundry architecture exclusively:

| Kind | Resource | Endpoint shape | Used by |
|---|---|---|---|
| **Account-based** (Foundry Agent Service) | `Microsoft.CognitiveServices/accounts/projects` | `https://<account>.services.ai.azure.com/api/projects/<project>` | the `azure-ai-projects` SDK + Responses API used by `src/orchestrator/foundry_agent.py` |

The agent SDK in this repo (`azure-ai-projects>=2.2.0`, `PromptAgentDefinition`, the Responses API)
talks to an **account-based** project. `FOUNDRY_PROJECT_ENDPOINT` must therefore be the
`…services.ai.azure.com/api/projects/…` URL.

The Bicep IaC (`infra/main.bicep`) provisions the AI Services account; the child project is created
via SDK or the Azure portal (not Bicep), because the account-based project model is provisioned
as a child resource of the CognitiveServices account.

### Provision the account-based project and a model

```powershell
# 1. Enable project management on the AI Services account (one-time).
$env:AZURE_RESOURCE_GROUP="<your-resource-group>"
$env:AI_SERVICES_ACCOUNT_NAME="<your-ai-services-account>"
$env:FOUNDRY_PROJECT_NAME="<your-foundry-project>"
$env:MODEL_DEPLOYMENT_NAME="gpt-4o"

$acct = az cognitiveservices account show -g $env:AZURE_RESOURCE_GROUP -n $env:AI_SERVICES_ACCOUNT_NAME --query id -o tsv
az resource update --ids $acct --set properties.allowProjectManagement=true --latest-include-preview

# 2. Create the account-based Foundry project.
az cognitiveservices account project create -g $env:AZURE_RESOURCE_GROUP --name $env:AI_SERVICES_ACCOUNT_NAME --project-name $env:FOUNDRY_PROJECT_NAME --location eastus2

# 3. Deploy a chat model (matches MODEL_DEPLOYMENT_NAME).
az cognitiveservices account deployment create -g $env:AZURE_RESOURCE_GROUP -n $env:AI_SERVICES_ACCOUNT_NAME --deployment-name $env:MODEL_DEPLOYMENT_NAME --model-name gpt-4o --model-version 2024-11-20 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 10
```

### Configure the environment

Set these (e.g. in a `.env` file at the repo root):

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>
MODEL_DEPLOYMENT_NAME=gpt-4o
# Optional — when omitted the agent uses a demo-safe fabric_query fallback so you
# can run live on day one before wiring real data.
# FABRIC_IQ_CONNECTION_ID=<fabric data agent connection id>
```

### Register the agent before you look for it in the portal

The portal only shows an agent **after** you register it from code. Agents are not created by the
infra deploy — they are created by the SDK path in `src/orchestrator/foundry_agent.py`. Register the
WWI single agent (and run a query) with either of:

```powershell
uv run python -m src.orchestrator "Compute quota attainment: target 1,000,000, ytd 600,000, pipeline 500,000, 6 months, 180 days"
# Or the reproducible end-to-end check (register -> list -> Playground query):
uv run python scripts/verify_foundry_agent.py
```

`verify_foundry_agent.py` is the canonical proof: it registers or reuses the fingerprinted `SalesAgent`
definition, lists the project agents to confirm portal visibility, and runs one Responses-API query (the same
call the Playground makes). The check intentionally clears preview platform-tool connection ids for this
single smoke query so it uses the deterministic local `fabric_query` / `get_account_activity` function tools.
A successful run prints `[OK] live registration + Playground response verified`.

**Facilitator proof:** before delivery, run `scripts/verify_foundry_agent.py` against your configured
`FOUNDRY_PROJECT_ENDPOINT`, capture the agent version from the output, confirm it appears in the project agent
catalog, and keep the portal trace ID in your private run notes.

Once it has run successfully at least once, open the Foundry portal (`https://ai.azure.com`):

1. Open the project named in `FOUNDRY_PROJECT_ENDPOINT`.
2. Open **Agents**. You should now see the `SalesAgent` registration. (If the list is empty, the
   registration step above has not completed — re-run it and check the CLI output for errors.)
3. Open the agent in **Playground** and run `Generate a quota report for Tailspin Toys`.
4. Open tracing or observability views and inspect the tool calls, latency, and generated artifact metadata.
5. Use **Publish** when the agent is ready for Microsoft 365 Copilot and Teams.

![Foundry playground verification view](/img/workshop/foundry-playground.svg)

*Schematic diagram — a labeled representation of the portal layout, not a screenshot. The live Foundry portal UI will differ in exact styling.*

Use this visual as the Day 2 checkpoint: the left pane confirms `SalesAgent` exists, the Playground prompt
proves the Responses API path works, and the trace pane confirms tool-call observability without logging payloads.

> **Fabric IQ vs. the demo fallback.** The `FabricIQPreviewTool` is a *platform* tool that requires a
> real Fabric Data Agent connection **and** a project/region where the preview tool is enabled on the
> Responses API. When `FABRIC_IQ_CONNECTION_ID` is unset, the agent instead registers a `fabric_query`
> function tool backed by demo-safe WWI rows, so registration and the Playground response work in any
> account-based project. Swap in the real connection id to query live data.

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

> **Scope honesty.** This repo does **not** ship a separate Foundry agent per box above. The single
> `SalesAgent` (`src/orchestrator/foundry_agent.py`) already performs every stage in-process by calling its
> tools, which is what you demo and unit-test. The diagram shows how the *same* outcome decomposes if you
> promote each stage to its own agent — see the promotion options below.

Run the real single-agent workflow that produces the same outcome:

```powershell
uv run python -m src.orchestrator "Generate a quota report for Tailspin Toys"
```

For genuinely separate sub-agents today, use the **Databricks Supervisor Agent**
(`src/orchestrator/databricks_supervisor.py`) or call the separately deployed
[`ericchansen/market-research`](https://github.com/ericchansen/market-research) agent.

### Promotion path to real Foundry multi-agent (verified against the SDK)

Because this repo is on the **new** Responses API path (`PromptAgentDefinition` + `create_version` +
`openai.responses.create`), the classic `ConnectedAgentTool` does **not** apply — it belongs to the deprecated
threads/runs API and its agents cannot be referenced from prompt agents. The new-API options are:

| Option | What it is | Setup cost | Status |
|---|---|---|---|
| **A2A tool** (`A2APreviewTool`) | One prompt agent calls another agent exposed as an A2A endpoint; one tool per sub-agent. | Each sub-agent needs an A2A **connection created in the Foundry portal** — no SDK-only path. | Public Preview |
| **Foundry Workflows** (`WorkflowAgentDefinition`) | Declarative sequential / group-chat / human-in-the-loop graph, authored as Power Fx **YAML** in the portal or VS Code Foundry Toolkit, invoked by name. | Portal/VS Code authoring; YAML is portal-proprietary. | Portal feature |
| **Microsoft Agent Framework** | Pure-Python orchestration (`SequentialBuilder`, `HandoffBuilder`) over `FoundryChatClient`, runs against the same Responses API. | `pip install agent-framework agent-framework-foundry`; no portal A2A setup. | Recommended code path |
| **Foundry Local** | On-device model runtime with an OpenAI-compatible local endpoint. | Install the Foundry Local CLI and download a compatible model. | Local model runtime, not portal agent chaining |

**Microsoft Agent Framework** is the recommended code path when you want real, separately-orchestrated agents
over the same Responses API. Install the extra and point it at your Foundry project; you compose planner →
data → research → work-context → report participants with `SequentialBuilder` (or `HandoffBuilder` for routing):

```powershell
uv sync --extra agent-framework
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
$env:FOUNDRY_MODEL = "gpt-4o"  # MODEL_DEPLOYMENT_NAME is also accepted
```

See the [Agent Framework sequential orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential) guide for the builder API.

For cloud-blocked workshops, [Foundry Local and DevUI](../workshop/foundry-local-devui) shows the offline path:
validate the tool contracts with the unit + contract test suite and, optionally, install Foundry Local for on-device
model experiments. Treat local proof as a tool-contract and artifact-generation check, not as evidence that the
Foundry portal, publishing, or eval loop is working.

Promoting to A2A connections or Foundry Workflows requires the portal setup noted above — create the A2A
connections (or author the workflow YAML) in the Foundry portal, then reference them by name from a
`PromptAgentDefinition` or `WorkflowAgentDefinition`. Use the **single-agent pattern** when speed, fewer
registrations, and simpler publishing matter more; use a **multi-agent** option when you need independent
observability, separate ownership, or agent-specific evaluation.

References (verified 2026):

- [Migrate to the new Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate) — Connected Agents is not available on the new API
- [Agent-to-agent (A2A) tool](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/agent-to-agent)
- [Foundry workflows concept](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow)
- [Agent Framework sequential orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential)
- [Foundry Local documentation](https://learn.microsoft.com/en-us/azure/foundry-local/)

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
| Databricks Supervisor | `src/orchestrator/databricks_supervisor.py` | Optional multi-sub-agent path over Unity Catalog data, configured in the Databricks UI / API |
| Report generator | `src/agents/report_generator/` | DOCX generation + OneDrive upload |
| Infra (Bicep) | `infra/` | AI Services account (modern Foundry), storage, Key Vault, Fabric capacity. Agents and projects are registered out-of-band (SDK / CLI / portal). |

## Publishing to Microsoft 365 and Teams

`scripts/verify_foundry_agent.py` verifies the prompt-agent registration and a Playground-style Responses API
query. To reach business users, **Publish** the verified `SalesAgent` from the Foundry portal to Microsoft 365
Copilot and Teams.

In the current Foundry Agent object model, the stable endpoint, Entra agent identity, version, and agent card
live on the **agent itself** — there is no separate hosted application resource to build or deploy. Publishing
means exposing the registered agent through M365/Teams channels via its agent card. See
[Migrate to the new Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate)
and [Publish agents to Microsoft 365 Copilot and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot).

## When to use the Foundry surface

- **Business users** — people who work in Teams and Outlook, not terminals
- **Enterprise distribution** — Entra identity, RBAC, compliance
- **Rich output** — DOCX reports, adaptive cards, OneDrive links
- **Production** — monitored, scalable, auditable

> 📖 [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) · [Publish agents to Microsoft 365 Copilot and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot) · [Tracing for AI agents](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup)
