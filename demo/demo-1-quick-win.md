# Demo 1 — Quick Win (5 minutes)

> **Audience:** Executives and business stakeholders
> **Goal:** Show the art of the possible — zero code, governed data, instant insights
> **Dataset:** Wide World Importers (wholesale novelty goods)

---

## Prerequisites

| Requirement | Details |
|---|---|
| Fabric capacity | F2 or higher, **active** (not paused) |
| Fabric Data Agent | Published as **WWISalesAgent** with the WWI lakehouse/warehouse connected |
| M365 Copilot license | For the presenter's account |
| Agent published to M365 | Data Agent → **Publish** → M365 Copilot Chat (see `docs/surfaces/m365-direct.md`) |

### Pre-flight checklist (do this 10 min before the demo)

- [ ] Open [M365 Copilot Chat](https://m365.cloud.microsoft/chat) in Edge — confirm you're signed in
- [ ] Type `@` and verify **WWISalesAgent** appears in the agent picker
- [ ] Send a quick test query ("How many customers do we have?") to warm the cache
- [ ] Clear the chat so the audience sees a fresh conversation

---

## Script

### 1. Set the scene (30 seconds)

> **Say:**
> "Wide World Importers is a wholesale novelty goods company. They have sales data across multiple territories, hundreds of customers, and thousands of order lines. We loaded this data into Microsoft Fabric and published a Data Agent — no code required. Let me show you what that looks like."

### 2. Open M365 Copilot Chat (30 seconds)

- Navigate to [m365.cloud.microsoft/chat](https://m365.cloud.microsoft/chat)
- Click the **@** mention button in the compose box
- Select **WWISalesAgent** from the list

> **Say:**
> "This agent is available to anyone in the org with a Copilot license. They find it right here, same place they use regular Copilot."

### 3. Top customers by revenue (1 minute)

Type:

```
@WWISalesAgent Who are our top 5 customers by revenue?
```

**Expected response:** A table or list with customer names and total revenue. Typical WWI results:

| Customer | Revenue |
|---|---|
| Tailspin Toys (Head Office) | ~$3.6M |
| Wingtip Toys (Head Office) | ~$3.4M |
| Contoso Ltd | ~$1.2M |
| ... | ... |

> **Say:**
> "No code. No dashboard. Just a natural language question. Notice the numbers are grounded in real data — this isn't hallucinated. The agent wrote a SQL query against the Fabric warehouse, ran it, and formatted the answer."

**Talking point — Governance:**
> "This data is governed by Fabric's security model. Row-level security, column-level security — whatever you've configured in Fabric, the agent respects it. If a salesperson only has access to their territory's data, that's all the agent will show them."

### 4. Chart of sales by territory (1.5 minutes)

Type:

```
@WWISalesAgent Show me a chart of sales by territory
```

**Expected response:** Code Interpreter generates a bar chart inline showing revenue by sales territory (Americas, Asia-Pacific, Europe, etc.).

> **Say:**
> "This is Code Interpreter — it's built into M365 Copilot. The agent fetched the data, and Copilot automatically generated a chart. No Power BI report needed for ad-hoc analysis."

**Pause to let the chart render.** Give the audience a moment to absorb it.

> **Talking point — Code Interpreter:**
> "Code Interpreter runs Python in a sandbox behind the scenes. It can generate charts, pivot tables, even statistical analysis. The user never sees the code — they just see the result."

### 5. Monthly sales trend (1 minute)

Type:

```
@WWISalesAgent How did sales trend month over month last year?
```

**Expected response:** A line chart or table showing monthly revenue with trend direction.

> **Say:**
> "Now we're doing time-series analysis. The agent understood 'last year,' translated it to the correct date range, aggregated by month, and showed the trend. A salesperson could ask this at 8 AM Monday morning and have their answer before coffee is ready."

### 6. Share the agent (30 seconds)

- Click the **⋯** (more options) or **Share** button on the agent
- Show the sharing dialog — highlight that it's just a link

> **Say:**
> "Sharing is a link. Send it in Teams, put it in an email, pin it in a channel. Anyone with a Copilot license and the right Fabric permissions can use it immediately."

### 7. Wrap-up (30 seconds)

> **Say:**
> "Let's recap what we just saw:
> - **Zero code** — no Python, no SQL, no Power BI reports
> - **Governed data** — row-level security, column-level security, all enforced by Fabric
> - **Built-in charting** — Code Interpreter generates visuals on the fly
> - **Instant sharing** — a link is all it takes
>
> This took about 10 minutes to set up — load data into Fabric, publish a Data Agent, click 'Publish to M365.' Your sales team can be using this today."

---

## If things go wrong

| Problem | Recovery |
|---|---|
| Agent doesn't appear in `@` picker | It can take 10–15 min after publishing. Have a backup browser tab with the Fabric portal open — demo there instead. |
| Query returns an error | Say "Let me rephrase that" and try a simpler version: "What are our total sales?" |
| Chart doesn't render | Say "Sometimes Code Interpreter takes a moment" — wait 5 seconds. If still nothing, ask for "a table instead of a chart." |
| Slow response | Fill the silence: "The agent is translating this to SQL, running the query against Fabric, and formatting the result — all in real time." |
| Wrong numbers | WWI data is a sample dataset — say "These are demo numbers from the Wide World Importers sample. In production, this would be your actual CRM data." |

---

## Key messages to land

1. **Zero code** — publish from Fabric portal to M365 Copilot in clicks
2. **Governed** — Fabric security model is respected end-to-end
3. **Already in their workflow** — M365 Copilot Chat is where your people already work
4. **10-minute setup** — not a months-long BI project
5. **This is just the starting point** — the technical demo shows multi-agent orchestration, reports, and more
