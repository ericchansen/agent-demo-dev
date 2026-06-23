# Demo 1 — Quick Win (5 minutes)

> **Audience:** Executives and business stakeholders
> **Goal:** Show the art of the possible — governed data, instant insights, zero custom code
> **Data:** Real sales/CRM data via Fabric Data Agent

---

## Prerequisites

| Requirement | Details |
|---|---|
| Fabric capacity | F2 or higher, **active** (not paused) |
| Fabric Data Agent | Published as **SalesAgent** with lakehouse connected |
| M365 Copilot license | For the presenter's account |
| Agent published to M365 | Data Agent → **Publish** → M365 Copilot Chat |

### Pre-flight checklist (10 min before)

- [ ] Open [M365 Copilot Chat](https://m365.cloud.microsoft/chat) in Edge
- [ ] Type `@` and verify **SalesAgent** appears in the agent picker
- [ ] Send a test query to warm the cache
- [ ] Clear the chat for a fresh start

---

## Script

### 1. Set the scene (30 seconds)

> **Say:**
> "We have sales data — territories, customers, pipeline, orders — in Microsoft Fabric. We published a Data Agent on top of it with no custom code. Let me show what you can do from M365 Copilot."

### 2. Open M365 Copilot Chat (30 seconds)

- Navigate to [m365.cloud.microsoft/chat](https://m365.cloud.microsoft/chat)
- Click **@** → select **SalesAgent**

> **Say:**
> "The agent is already in M365 Copilot. No separate app, no Teams bot setup — just publish from the Fabric portal."

### 3. Simple query (1 minute)

**Type:** `What were total sales for the Northwest territory last quarter?`

> **Say:**
> "Natural language to SQL, governed by Fabric's security model. The agent only sees data the user has access to."

### 4. Follow-up (1 minute)

**Type:** `Break that down by customer. Who are the top 5?`

> **Say:**
> "It keeps conversational context. Each follow-up refines the query — no need to restate the territory or time range."

### 5. Cross-territory comparison (1 minute)

**Type:** `Compare that to the Southwest territory. Which is growing faster?`

> **Say:**
> "This is a JOIN across territories with a growth rate calculation — complex SQL generated from a simple question."

### 6. Wrap up (30 seconds)

> **Say:**
> "Five minutes, zero code. The data stays in Fabric, governed by your security model. The agent is published to M365 and available to anyone with the right permissions. Next, I'll show the engineering view — how we extend this with custom skills and external data."