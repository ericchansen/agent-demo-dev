# Two-Surface Demo: CLI Prototype to Foundry Production

This repo narrows the demo story to two surfaces that share the same **Wide World Importers** sales workflow:

- **Prototype surface:** GitHub Copilot CLI with MCP servers
- **Production surface:** Azure AI Foundry agent published to **M365 Copilot + Teams** through an Agent Application

The important idea is not two separate products. It is **one business flow** that starts in the terminal, proves out the tools quickly, and then graduates into a managed M365 experience.

## Capability Translation Map

| Capability | CLI prototype (MCP) | Foundry production | Notes |
|---|---|---|---|
| Fabric sales data | `wwi-sales-data` MCP server | `FabricIQPreviewTool` | Same Fabric Data Agent backend and business questions |
| M365 activity context | `workiq` MCP server (**mocked in demo**) | `WorkIQPreviewTool` | Production target is WorkIQ with OBO auth; demo tenant uses sample activity payloads |
| Report generation | `quota-forecast` skill returns inline markdown / summary | Custom function tool generates DOCX locally (deploy with OneDrive upload for sharing links) | Same reporting logic, different delivery format |
| Tool bridging during migration | Existing MCP servers | `MCPTool` | Useful when you want to reuse an MCP endpoint before converting it to a native platform tool or custom function |
| Agent packaging | CLI skill + local MCP config | `PromptAgentDefinition` + Agent Application publish | Same instructions can move from prototype prompt to managed agent definition |

## Prototype → Graduate Narrative

### 1. Prototype fast in Copilot CLI

Use the CLI surface to validate prompts, tool schemas, and answer quality while you still want fast iteration:

- Swap Fabric Data Agent endpoints without redeploying Azure resources
- Inspect raw MCP responses in the terminal
- Keep report output inline until the flow is stable

### 2. Stabilize the contract

Before graduating, keep the capabilities aligned across both surfaces:

- Ask the **same business questions** on both paths
- Keep the **same output schema** for M365 activity context, even when the demo uses mock data
- Separate **report content generation** from **report delivery** so the CLI can render inline while Foundry writes DOCX files

### 3. Graduate to Foundry for M365 and Teams

Once the flow is proven:

- Replace CLI MCP usage with **`FabricIQPreviewTool`** and **`WorkIQPreviewTool`**
- Move report creation into **custom function tools**
- Wrap the instructions and tools in **`PromptAgentDefinition`**
- Publish through an **Agent Application** so business users can reach it from **M365 Copilot** and **Teams**

### 4. Keep WorkIQ honest in the demo

The demo tenant cannot currently provision the WorkIQ service principal. For the demo:

- Docs still describe **WorkIQ as the production integration**
- The prototype surface uses a **mock WorkIQ MCP tool** with representative M365 activity data
- The production surface should keep the **same shape and intent** so swapping in `WorkIQPreviewTool` is a configuration change, not a redesign

## Same Query, Two Surfaces

### GitHub Copilot CLI (prototype)

```text
copilot "Use wwi-sales-data and workiq to find WWI accounts with high pipeline value but low recent activity. Then produce a quota-forecast summary inline."
```

In the CLI path, Copilot routes the question through MCP servers and returns the synthesized answer directly in the terminal.

### Azure AI Foundry (production)

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FabricIQPreviewTool,
    PromptAgentDefinition,
    WorkIQPreviewTool,
)

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(
        endpoint=foundry_project_endpoint,
        credential=credential,
        allow_preview=True,
    ) as project_client,
):
    openai_client = project_client.get_openai_client()

    agent = project_client.agents.create_version(
        agent_name="WWISalesAgent",
        definition=PromptAgentDefinition(
            model="gpt-4o",
            instructions=(
                "Use Fabric IQ for WWI sales data, WorkIQ for M365 activity, "
                "and the report tool when the user asks for a formatted deliverable."
            ),
            tools=[
                FabricIQPreviewTool(
                    project_connection_id=fabric_iq_connection_id,
                    require_approval="never",
                ),
                WorkIQPreviewTool(
                    project_connection_id=workiq_connection_id,
                ),
                report_function_tool,
            ],
        ),
    )

    response = openai_client.responses.create(
        input=(
            "Find WWI accounts with high pipeline value but low recent activity, "
            "then create a quota forecast report."
        ),
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(response.output_text)
```

If you want an intermediate migration step, `MCPTool` can bridge an existing MCP endpoint into Foundry before you replace it with a native platform tool or custom function.

The user question stays effectively the same. What changes is the **distribution model**: CLI during prototyping, Foundry + Agent Application for M365 Copilot and Teams.

## Demo Scope Reminder

This two-surface path is the implemented demo story for this repo. Existing docs in [`docs/surfaces/`](surfaces/) stay in place as reference material for adjacent patterns such as Copilot Studio and M365 direct publish.
