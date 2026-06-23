# Surface: M365 Copilot (Direct Fabric Publish)

> **Zero-code path.** Publish a Fabric Data Agent directly to M365 Copilot Chat — no orchestrator, no custom code.

**Citation:** <https://learn.microsoft.com/en-us/fabric/data-science/data-agent-microsoft-365-copilot>

---

## How It Works

Fabric's built-in "Publish to Agent Store" feature pushes a Data Agent straight into the M365 Copilot ecosystem. End users `@mention` the agent in M365 Copilot Chat, and Copilot translates natural-language questions into SQL against your Fabric lakehouse/warehouse.

```
User → M365 Copilot Chat → @SalesAgent → Fabric Data Agent → Lakehouse SQL → Answer
```

No Azure AI Foundry, no Copilot Studio — just Fabric + M365.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Fabric capacity** | F2 or higher (F64 may be required in some tenants during preview) |
| **M365 Copilot license** | Required for every end user who will interact with the agent |
| **Same tenant** | Fabric workspace and M365 tenant must match |
| **Admin enablement** | Copilot extensibility must be enabled by your M365 admin |
| **Data Agent created** | A Fabric Data Agent must already exist in your workspace |

---

## Step-by-Step

### 1. Create the Data Agent

1. Open the **Fabric portal** → navigate to your workspace.
2. Select **+ New item** → **Data Agent**.
3. Configure the agent:
   - Add your lakehouse or warehouse as a data source.
   - Provide instructions (system prompt) describing the data and how to answer questions.
   - Add example questions to guide the NL→SQL translation.
4. **Test** the agent in the Fabric preview pane to confirm queries return correct results.

### 2. Publish to the Agent Store

1. In the Data Agent editor, click **Publish**.
2. Check **"Publish to Agent Store"** — this makes the agent discoverable in M365 Copilot.
3. Fill in the metadata:
   - **Name**: e.g., `Sales Agent`
   - **Description**: e.g., "Ask questions about sales sales data."
   - **Icon** (optional): Upload a custom icon.
4. Click **Publish**.

### 3. Wait for Propagation

The agent may take **up to 24 hours** to appear in the M365 Copilot agent store. During preview, propagation times vary.

### 4. Use in M365 Copilot Chat

1. Open **M365 Copilot Chat** (at [m365.cloud.microsoft/chat](https://m365.cloud.microsoft/chat)).
2. Type `@` and search for your agent name (e.g., `@SalesAgent`).
3. Ask a question: `@SalesAgent What were total sales by region last quarter?`
4. Copilot translates the question to SQL, executes against Fabric, and returns the answer.

---

## Capabilities

| Capability | Supported |
|---|---|
| Natural-language → SQL queries against Fabric data | ✅ |
| Code Interpreter for charts and visualizations | ✅ |
| Shareable via link | ✅ |
| M365 Copilot Chat integration | ✅ |
| Web research | ❌ |
| SharePoint search | ❌ |
| Report generation (DOCX/PPTX) | ❌ |
| Multi-agent orchestration | ❌ |
| Custom function calling | ❌ |

### User Experience

- Users `@mention` the agent in M365 Copilot Chat — e.g., `@SalesAgent`.
- Copilot's **Code Interpreter** can render charts from query results.
- Agents can be **shared via link** to other licensed users in the tenant.
- The M365 orchestrator may rephrase or summarize answers before presenting them.

---

## Limitations

| Limitation | Impact |
|---|---|
| **Single Fabric Data Agent only** | Cannot combine multiple agents or data sources in one interaction |
| **No orchestration** | No multi-step workflows, no chaining tools |
| **No report generation** | Cannot produce DOCX, PPTX, or other file outputs |
| **M365 orchestrator rephrasing** | Copilot may rephrase, summarize, or add caveats to agent responses |
| **Fabric data only** | No access to external APIs, web search, or SharePoint |
| **Propagation delay** | Up to 24 hours after publishing before agent appears in Copilot |
| **Preview limitations** | Feature is in preview — behavior and availability may change |

---

## When to Use This Surface

✅ **Use when:**
- You want the fastest path from Fabric data to M365 Copilot.
- Your users only need to query structured data (no web research or document generation).
- You have no developer resources or prefer a zero-code approach.
- You're running a quick demo or proof-of-concept.

❌ **Don't use when:**
- You need multi-source answers (data + web + SharePoint).
- You need report generation (DOCX, PPTX).
- You need custom orchestration logic or multi-agent workflows.
- You want fine-grained control over how answers are formatted.

→ For those scenarios, see [Copilot Studio](copilot-studio.md) or [Azure AI Foundry](foundry.md).
