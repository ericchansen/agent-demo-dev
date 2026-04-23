# Demo 2 — Full Workflow (15 minutes)

> **Audience:** Data science and engineering teams
> **Goal:** Show the multi-agent orchestration pipeline — CLI, M365, and architecture options
> **Dataset:** Wide World Importers (wholesale novelty goods)

---

## Prerequisites

| Requirement | Details |
|---|---|
| Fabric capacity | F2 or higher, **active** |
| Fabric Data Agent | Published as **WWISalesAgent** |
| Researcher Agent | Running locally (`make serve-researcher`) |
| SharePoint Agent | Running locally (`make serve-sharepoint`) |
| CLI configured | `.copilot/mcp-config.json` with all three MCP servers registered |
| VS Code or terminal | With GitHub Copilot CLI installed |
| Demo SharePoint docs | Sample proposals loaded (`demo/sharepoint-docs/`) |
| M365 Copilot license | For showing the M365 surface |

### Pre-flight checklist (do this 15 min before the demo)

- [ ] Start sub-agents in separate terminals:
  ```bash
  make serve-researcher   # Terminal 1
  make serve-sharepoint   # Terminal 2
  ```
- [ ] Verify MCP config: open `.copilot/mcp-config.json` and confirm all three servers are listed
- [ ] Open VS Code with the repo — run a quick test query to warm things up
- [ ] Open [M365 Copilot Chat](https://m365.cloud.microsoft/chat) in a browser tab
- [ ] Have the "Choose Your Architecture" doc open: `docs/surfaces/README.md`
- [ ] Pre-generate a sample DOCX so you have a fallback if generation is slow

---

## Part 1 — CLI Multi-Agent Pipeline (7 minutes)

### 1. Set the scene (30 seconds)

> **Say:**
> "In the last demo, we saw a single Data Agent answering questions from Fabric. That's great for ad-hoc queries. But what if a salesperson needs a full account plan — pipeline data, competitive intelligence, prior proposals, all in one document? That's where multi-agent orchestration comes in."

### 2. Open VS Code / Terminal (30 seconds)

- Open VS Code with the accelerator repo
- Open the integrated terminal or a standalone terminal
- Show the MCP config briefly:

```bash
cat .copilot/mcp-config.json
```

> **Say:**
> "Here's our MCP configuration. Three servers: the Fabric Data Agent for pipeline data, a Researcher Agent for web intelligence, and a SharePoint Agent for internal documents. These are standard MCP servers — the same protocol GitHub Copilot, VS Code, and Claude all speak."

### 3. Generate an account plan (3 minutes)

Type in Copilot CLI or VS Code Copilot Chat:

```
Generate an account plan for Tailspin Toys
```

**What happens (narrate as it runs):**

> **Say:**
> "Watch what happens. The orchestrator is:
> 1. **Calling the Fabric Data Agent** — pulling Tailspin Toys' purchase history, revenue trend, top products ordered, and territory data
> 2. **Calling the Researcher Agent** — searching the web for recent news about Tailspin Toys, industry trends in the toy wholesale market, competitive landscape
> 3. **Calling the SharePoint Agent** — finding any prior proposals, meeting notes, or account reviews we've shared internally
>
> Each agent returns structured data with citations — where the information came from."

**Pause while it runs.** Fill silence by pointing to the terminal output showing tool calls.

> **Say:**
> "Notice each tool call is logged. You can see exactly what the agent asked for and what it got back. Full traceability."

### 4. Show the generated document (2 minutes)

Open the generated DOCX file (or the terminal output if DOCX generation is slow):

> **Say:**
> "Here's the output — a DOCX account plan. Let me walk you through it:
>
> - **Account summary** — revenue, territory, key contacts. All from Fabric.
> - **Recent activity** — last 12 months of order data, trend direction. From Fabric.
> - **Market intelligence** — recent news, competitor moves. From the Researcher Agent.
> - **Internal context** — prior proposals and meeting notes. From SharePoint.
> - **Recommendations** — synthesized by the LLM using all three sources.
>
> Every claim has a citation. Click any footnote and it links back to the source — the Fabric query, the web article, or the SharePoint document."

**Talking point — Citations:**
> "Citations aren't optional. In a regulated industry, you need to know where every number came from. This is baked into the template, not an afterthought."

### 5. Talking points for Part 1 (30 seconds)

> **Say:**
> "So what did we just see?
> - **MCP protocol** — open standard, not proprietary. Any MCP-compatible client can use these agents.
> - **Sub-agent pattern** — each agent does one thing well. The orchestrator composes them.
> - **Template-based generation** — the DOCX follows a predefined template with citation formatting built in.
> - **This ran locally** — no cloud orchestrator needed for the CLI surface."

---

## Part 2 — M365 Copilot & Copilot Studio (4 minutes)

### 6. Switch to M365 Copilot Chat (2 minutes)

- Switch to the browser tab with M365 Copilot Chat
- Type `@` and select **WWISalesAgent**

```
@WWISalesAgent What's Tailspin Toys' order history for the last 6 months?
```

> **Say:**
> "Same Fabric Data Agent, different front door. The business user doesn't need VS Code or a terminal — they get the data answers right here in M365 Copilot Chat, where they already work."

Show the response, then:

> **Say:**
> "This surface gives you Fabric data queries and Code Interpreter charts — but it doesn't have the Researcher or SharePoint agents. For that, you need Copilot Studio or Azure AI Foundry."

### 7. Show Copilot Studio option (1 minute)

- Open [Copilot Studio](https://copilotstudio.microsoft.com) in a new tab (or show a screenshot)
- Show the agent configuration with connectors

> **Say:**
> "Copilot Studio is the low-code option. You wire up the Fabric Data Agent as a connected agent, add a SharePoint connector for internal docs, add a Bing connector for web search. No Python required. It publishes to M365 Copilot Chat and Teams.
>
> The trade-off: no report generation, and orchestration logic is limited to what the visual designer supports."

### 8. Show the Foundry option (1 minute)

- Show `src/orchestrator/` in VS Code briefly

> **Say:**
> "Azure AI Foundry is the pro-code option. Full Python SDK, multi-agent orchestration, report generation, custom logic. This is what we used in the CLI demo — the same orchestrator can be published to M365 Copilot, Teams, or a custom web app.
>
> The trade-off: you need Python developers and an Azure subscription."

---

## Part 3 — Architecture Overview (4 minutes)

### 9. Show the "Choose Your Architecture" doc (2 minutes)

Open `docs/surfaces/README.md` (or the rendered version) and show the comparison table:

> **Say:**
> "Here's the key insight: **same backend, different front doors.** The Fabric Data Agent is the foundation for all four surfaces. You're not rebuilding anything — you're choosing how users access it."

Walk through the comparison table columns:

> - "**GitHub Copilot** — developer audience, full pipeline, 10 minutes to set up."
> - "**M365 Direct** — business users, Fabric-only queries, zero code."
> - "**Copilot Studio** — business users, multi-source, low code."
> - "**Azure AI Foundry** — full pipeline with reports, pro code, publish anywhere."

### 10. Show the architecture diagram (1 minute)

Open the architecture diagram from `docs/diagrams/` (or draw it on a whiteboard):

```
┌─────────────────────────────────────────────────────────┐
│                    Consumption Surfaces                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Copilot  │ │  M365    │ │ Copilot  │ │  Foundry │   │
│  │  CLI     │ │  Direct  │ │  Studio  │ │  Agent   │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │
│       │             │            │             │          │
│       └──────┬──────┴────────────┴──────┬──────┘          │
│              ▼                          ▼                 │
│  ┌───────────────────┐   ┌──────────────────────────┐    │
│  │  Fabric Data Agent │   │  Custom MCP Sub-Agents   │    │
│  │  (NL → SQL/DAX)   │   │  Researcher + SharePoint │    │
│  └────────┬──────────┘   └────────────┬─────────────┘    │
│           ▼                           ▼                   │
│  ┌───────────────────┐   ┌──────────────────────────┐    │
│  │  OneLake / WWI    │   │  Web + SharePoint + Docs │    │
│  │  (Fabric)         │   │  (External Sources)       │    │
│  └───────────────────┘   └──────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

> **Say:**
> "Everything below the surface layer is shared. The Fabric Data Agent talks to OneLake. The custom sub-agents talk to web APIs and SharePoint. The surface you pick just determines how users interact with it."

### 11. Wrap-up (1 minute)

> **Say:**
> "To summarize:
> - **Fabric Data Agent** is the foundation — NL→SQL over your governed data.
> - **Sub-agents** add research, SharePoint, and report generation via MCP.
> - **Four surfaces** let you meet users where they are — terminal, M365 Chat, Teams, or custom apps.
> - **Same backend, different front doors** — pick one, or use all four.
>
> The engineering deep dive goes into the code, the IaC, the eval harness, and how to extend it."

---

## If things go wrong

| Problem | Recovery |
|---|---|
| Sub-agent doesn't respond | Check the terminal running the agent. Restart with `make serve-researcher`. Fill time by showing the MCP config instead. |
| DOCX generation is slow | "Report generation involves multiple API calls — let me show you a pre-generated example while this finishes." Open a pre-generated DOCX from `demo/sample-data/`. |
| M365 Copilot agent not found | "The agent can take a few minutes to appear after publishing. Let me show it in the Fabric portal instead." Open the Fabric Data Agent chat directly. |
| Copilot Studio is slow to load | Show a screenshot instead. Have screenshots in `demo/screenshots/`. |
| Account plan has wrong data | "Remember, this is the Wide World Importers sample dataset. In production, you'd connect your own CRM and pipeline data." |

---

## Key messages to land

1. **MCP protocol** — open standard, not vendor lock-in
2. **Sub-agent composition** — each agent does one thing well, the orchestrator composes
3. **Citations are first-class** — every claim traces back to a source
4. **Same backend, different front doors** — four surfaces, one data platform
5. **Template-based generation** — reports follow a consistent, branded format
6. **Choose your complexity** — zero-code to pro-code, all supported
