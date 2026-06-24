# Surface: Copilot Studio (Low-Code)

> **Low-code orchestration.** Connect a Fabric Data Agent to Copilot Studio, add SharePoint and web connectors, and publish to M365 Copilot Chat or Teams.

**Citation:** <https://learn.microsoft.com/en-us/fabric/data-science/data-agent-microsoft-copilot-studio>

---

## How It Works

Copilot Studio acts as a low-code orchestration layer. You create a Copilot Studio agent, wire in the Fabric Data Agent as a "connected agent," then add additional connectors (SharePoint, web search, custom APIs) through the Studio UI. The result is a multi-source agent that users access in M365 Copilot Chat or Teams.

```
User → M365 Copilot Chat / Teams
  → Copilot Studio Agent
    → Fabric Data Agent (connected agent) → Lakehouse SQL
    → SharePoint connector → Document search
    → Web connector → Internet research
  → Combined answer
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Copilot Studio license** | Required for agent authoring and hosting |
| **Fabric capacity** | F2 or higher |
| **M365 Copilot license** | Required for end users accessing the agent via M365 Copilot Chat |
| **Fabric Data Agent** | Must already exist and be published in your Fabric workspace |
| **Admin enablement** | Copilot extensibility and Copilot Studio connectors enabled by admin |

---

## Setup Overview

### 1. Create a Copilot Studio Agent

1. Open [Copilot Studio](https://copilotstudio.microsoft.com/).
2. Click **+ Create** → **New agent**.
3. Name the agent (e.g., `Sales Agent`) and provide a description.

### 2. Add Fabric Data Agent as a Connected Agent

1. In the agent editor, go to **Connected agents** (or **Actions** depending on your Studio version).
2. Click **+ Add connected agent**.
3. Select your published Fabric Data Agent from the list.
4. Configure the trigger — typically "when the user asks about sales data" or similar intent.

### 3. Add Additional Connectors

| Connector | Purpose |
|---|---|
| **SharePoint** | Search company documents, policies, presentations |
| **Web search (Bing)** | Research competitors, market trends, news |
| **Custom connectors** | Call internal APIs, CRM systems, etc. |

For each connector:
1. Go to **Actions** → **+ Add action**.
2. Select the connector type and configure authentication.
3. Define when the action should be invoked (topic triggers or orchestrator routing).

### 4. Configure Conversation Topics

1. Create **topics** for common question patterns:
   - "Sales data questions" → routes to Fabric Data Agent
   - "Company policy questions" → routes to SharePoint
   - "Market research" → routes to web search
2. Use **generative orchestration** to let the Studio LLM decide which topic applies.

### 5. Publish

1. Click **Publish** in the top-right.
2. Select channels:
   - **M365 Copilot Chat** — users `@mention` the agent
   - **Teams** — available as a Teams app
   - **Custom website** — embed via iframe
3. Wait for propagation (similar to direct publish, may take hours).

---

## Capabilities

| Capability | Supported |
|---|---|
| Natural-language → SQL queries (via Fabric Data Agent) | ✅ |
| SharePoint document search | ✅ (via connector) |
| Web research | ✅ (via Bing connector) |
| Conversation topics and routing | ✅ |
| M365 Copilot Chat | ✅ |
| Teams channel/chat | ✅ |
| Custom website embed | ✅ |
| Multi-source answers | ✅ |
| Visual topic authoring | ✅ |
| Report generation (DOCX/PPTX files) | ❌ |
| Custom Python orchestration | ❌ |
| Full multi-agent workflows | ⚠️ Limited (connected agents, not true multi-agent) |

---

## Limitations

| Limitation | Impact |
|---|---|
| **No file output** | Cannot generate DOCX, PPTX, or other downloadable reports |
| **Text responses only** | Answers are text-based; no rich file attachments |
| **Less flexible orchestration** | Topic routing is simpler than Foundry's function-calling orchestration |
| **Connected agent constraints** | Fabric Data Agent runs as a sub-agent — limited control over its behavior |
| **Connector limitations** | Each connector has its own auth, rate limits, and data format constraints |
| **Studio version dependencies** | Features vary between Copilot Studio versions and preview rings |

---

## When to Use This Surface

✅ **Use when:**
- Business users or citizen developers want a low-code setup.
- You need multi-source answers (Fabric + SharePoint + web) without writing code.
- You want to publish to both M365 Copilot Chat and Teams with minimal effort.
- The full Azure AI Foundry SDK pipeline is overkill for your scenario.
- You want visual topic authoring and conversation design.

❌ **Don't use when:**
- You need to generate downloadable reports (DOCX, PPTX).
- You need complex multi-step orchestration with custom Python logic.
- You need fine-grained control over tool selection and execution order.
- You're building a production pipeline that requires version-controlled code.

→ For report generation and full orchestration, see [Azure AI Foundry](foundry.md).
→ For the simplest zero-code path, see [M365 Direct Publish](m365-direct.md).
