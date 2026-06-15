---
sidebar_position: 4
title: Cost Model
---

# Cost Model

What this accelerator costs to run, and how to minimize it.

## Monthly cost breakdown

| Resource | Monthly Cost | Notes |
|---|---|---|
| Fabric F2 capacity | ~$262 | **Pause when not demoing** to save ~70% |
| Databricks SQL warehouse / Genie | Usage-based | Only needed if you choose the Databricks path; stop the SQL warehouse after labs. Managed MCP itself is a control-plane surface; warehouse/model usage still drives cost. |
| Databricks Supervisor Agent / API | Usage-based | Advanced optional path. Serverless compute, Model Serving, AI Gateway, Genie, and UC tool calls can all contribute usage. |
| Azure OpenAI (gpt-4o) | ~$5–15 | Demo-scale (~50 queries/day) |
| Foundry Agent Service | Per-call | No standing cost for prompt agents |
| Foundry Hosted Agent | Container/runtime dependent | Only applies when you run the bring-your-own-code hosted-agent path; scale to zero or stop the host between labs. |
| Foundry Memory / evaluations | Usage-based | Optional Day 2 extension; eval calls add model/scoring usage. Memory is preview; do not assume pricing or API stability until confirmed in your region. |
| Key Vault | &lt;$1 | Negligible |
| Storage | &lt;$1 | Negligible |
| **Total (active)** | **~$270–300/mo** | Varies with Databricks warehouse size, hosted-agent runtime, and model/eval volume. |
| **Total (paused)** | **~$5–15/mo** | Fabric paused |

## Pause & resume

Fabric capacity is the largest cost. Pause it when not in use:

```bash
# Pause (stops billing immediately)
az fabric capacity suspend \
  --resource-group <your-resource-group> \
  --capacity-name <your-fabric-capacity-name>

# Resume (~1-2 min for cold start)
az fabric capacity resume \
  --resource-group <your-resource-group> \
  --capacity-name <your-fabric-capacity-name>
```

> ⚠️ Resume 10-15 minutes before a demo — the first query after resume can be slow (cold start).

## Cost optimization tips

- **Pause Fabric** when not actively demoing — this alone saves ~$200/month
- **Stop Databricks SQL warehouses** when using the Genie path outside lab windows
- **Use Databricks Managed MCP for Genie smoke** when available; it reduces custom adapter surface, but still stop the underlying warehouse when idle
- **Gate Databricks Supervisor labs** behind facilitator approval because serverless, Model Serving, Genie, and AI Gateway usage can stack
- **Use F2** (smallest capacity) — sufficient for demo workloads
- **Share a workspace** — multiple presenters can use the same Fabric capacity
- **Monitor with Cost Management** — set budget alerts in Azure portal or pass `budgetAlertEmails` to the Bicep template
- **Run what-if before deploys** — the deploy workflow includes a non-blocking `az deployment group what-if`, and facilitators should review it before customer workshops

## Demo-day cost guardrails

| Moment | Action |
|---|---|
| Night before | Resume Fabric or start Databricks only long enough to validate golden prompts, then pause/stop again. |
| 30 min before | Resume/start the chosen data backend and warm the first query. |
| Lunch break | Keep capacity running only if attendees will use hands-on labs immediately after lunch. |
| End of day | Pause Fabric, stop Databricks SQL warehouses, and review Cost Management. |

## Foundry Memory and evaluation guardrails

Foundry Agent Service lists memory as a preview built-in tool, but stable standalone Memory API/pricing details were
not published when these docs were updated. For workshops:

| Feature | Guidance |
|---|---|
| Foundry evaluations | Budget for additional model calls because every eval invokes or scores agent responses. Keep the golden set small and focused. |
| Foundry Memory | Treat as preview. Enable it only for an explicit Day 2 extension, document what gets remembered, and verify region/model availability in the portal. |
| Hosted-agent traces | Trace data lands in Application Insights or Azure Monitor; telemetry volume and retention affect cost. |
| Web search tools | Grounding/search tools may bill separately from the model call. |

Do not promise a flat Memory price in customer material. Check the current
[Microsoft Foundry pricing page](https://azure.microsoft.com/en-us/pricing/details/microsoft-foundry/) and the
[Foundry Agent Service overview](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) during facilitator
prep.

## Budget guardrail

`infra/modules/budget.bicep` can create a resource-group Azure Cost Management budget with actual-spend and
forecasted-spend notifications. It is opt-in so the repo does not store facilitator email addresses:

```powershell
az deployment group create `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --template-file infra/main.bicep `
  --parameters infra/parameters/dev.bicepparam `
  --parameters budgetAlertEmails='["facilitator@example.com"]'
```

The dev default is `$350/month`, alerting at 80% actual spend and 100% forecasted spend.

> 📖 [Fabric capacity pricing](https://learn.microsoft.com/fabric/enterprise/licenses) · [Databricks DBU pricing](https://learn.microsoft.com/en-us/azure/databricks/resources/pricing) · [Azure budget tutorial](https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets) · [Microsoft Foundry pricing](https://azure.microsoft.com/en-us/pricing/details/microsoft-foundry/) · [Microsoft Foundry overview](https://learn.microsoft.com/en-us/azure/foundry/)
