# Cost Model & Resource Management

Estimated monthly costs for running this accelerator. Actual costs depend on usage, region, commitment tier, and whether you pause resources when not in use.

> 📖 **Choosing a data platform?** This page covers the **Microsoft Fabric** path in depth. For the **Databricks Genie** path see the Genie cost guidance below and the published workshop docs: [Cost Model](https://ericchansen.github.io/agent-demo-dev/docs/workshop/costs) and [Databricks Genie](https://ericchansen.github.io/agent-demo-dev/docs/building-blocks/databricks-genie).

---

## Azure Resource Costs

| Resource | SKU / Tier | Estimated Monthly Cost | Notes |
|---|---|---|---|
| **Fabric Capacity** | F2 | ~$262/mo | Minimum for Data Agent. Can be paused. |
| **Fabric Capacity** | F64 | ~$8,400/mo | Required if F2 doesn't support Data Agent in your tenant (preview limitation) |
| **Azure AI Foundry Hub** | — | ~$0 | No standing cost — you pay for compute and model usage only |
| **Azure OpenAI (GPT-4o)** | Pay-as-you-go | ~$5–50/mo | Demo-scale usage (~10–100 queries/day) |
| **Azure Key Vault** | Standard | ~$0.03/10K operations | Negligible at demo scale |
| **Azure Bot Service** | Free tier (F0) | $0 | Free tier supports up to 10K messages/mo |
| **Azure Storage** | Hot tier | <$1/mo | For agent artifacts, logs |

### Cost Range Summary

| Scenario | Estimated Monthly Cost |
|---|---|
| **Demo / POC (F2 + GPT-4o light usage)** | ~$270–320/mo |
| **Demo / POC (F64 required)** | ~$8,450–8,500/mo |
| **Production (F64 + moderate GPT-4o)** | ~$8,500–9,000/mo |

> **💡 Tip:** The single biggest cost driver is Fabric capacity. If F2 supports Data Agent in your tenant, you save ~$8,100/mo.

---

## Token Usage Estimates

Typical token consumption per query type (GPT-4o pricing: ~$2.50/1M input, ~$10/1M output):

| Query Type | Input Tokens | Output Tokens | Est. Cost/Query |
|---|---|---|---|
| Simple data question | ~500 | ~200 | ~$0.003 |
| Multi-step (data + research) | ~2,000 | ~800 | ~$0.013 |
| Full pipeline (data + research + report) | ~5,000 | ~2,000 | ~$0.033 |

At **50 queries/day** (mixed types), expect **~$15–25/month** in Azure OpenAI costs.

---

## Databricks Genie path costs

If you choose the **Databricks Genie** data platform instead of (or alongside) Fabric, the cost model is **serverless pay-as-you-go billed in DBUs**, not a flat capacity SKU. Two lines stack:

| Cost line | How it's billed | Notes |
|---|---|---|
| **Genie LLM usage** | Per-DBU after a per-user free allowance | Each identified user gets **150 free Genie DBUs/month** (~80–100 questions, ~$10.50/mo value at $0.07/DBU, US East). Overage bills at the standard Genie DBU rate. |
| **SQL warehouse compute** | Per-DBU at the warehouse rate | The warehouse that executes Genie-generated SQL is billed separately. Right-size it and **stop it when idle**. |

> ⚠️ **Genie billing starts July 6, 2026.** Before that date Genie usage was not billed. The free 150-DBU/user/month allowance applies to **Genie, Genie Spaces, and Genie Code**, is per identified user (not per service principal), and resets monthly. Verify current rates and regional pricing on the [Genie pricing page](https://www.databricks.com/product/pricing/genie) before quoting numbers to a customer.

### Control Genie spend

- **Set Genie budgets** — admins can cap and alert on Genie spend per user, group, workspace, or the whole account. See [Manage budgets and cost controls for Genie](https://learn.microsoft.com/en-us/azure/databricks/genie/budgets).
- **Stop the SQL warehouse** between lab windows — warehouse DBUs, not the free LLM allowance, are usually the larger line for a workshop room driving many live questions.
- **Prefer the deterministic offline fallback** for large groups so you teach the architecture without burning DBUs.
- The optional **Databricks Supervisor Agent/API** path adds serverless, Model Serving, and AI Gateway usage on top of Genie — gate it behind facilitator approval.

> 📖 [Databricks DBU pricing](https://learn.microsoft.com/en-us/azure/databricks/resources/pricing) · [Genie pricing](https://www.databricks.com/product/pricing/genie) · [Genie budgets & cost controls](https://learn.microsoft.com/en-us/azure/databricks/genie/budgets)

---

## Licensing Costs (Not Azure)

These are Microsoft 365 / Copilot licenses — billed separately from Azure.

| License | Required For | Approx. Cost |
|---|---|---|
| **M365 Copilot** | End users accessing the agent via M365 Copilot Chat | ~$30/user/mo |
| **Copilot Studio** | Authoring agents in Copilot Studio surface | Included with M365 Copilot or separate license |
| **GitHub Copilot** | Developers using the CLI/VS Code surface | ~$19–39/user/mo |

---

## Teardown to Save Money

When you're not actively using the accelerator, **pause Fabric capacity** to stop billing:

### Pause via Makefile

```bash
make infra-teardown
```

This runs `az fabric capacity suspend` to pause the Fabric capacity.

### Pause via Azure CLI

```bash
# Pause Fabric capacity
az fabric capacity suspend \
  --resource-group rg-fabric-sales-agent \
  --capacity-name fabric-sales-agent-f2

# Verify it's paused
az fabric capacity show \
  --resource-group rg-fabric-sales-agent \
  --capacity-name fabric-sales-agent-f2 \
  --query "properties.state" \
  --output tsv
# Expected output: Paused
```

### What Happens When Paused

- ❌ Fabric queries stop working (Data Agent goes offline)
- ❌ M365 Copilot agent stops responding
- ✅ Data is preserved (lakehouse/warehouse data is safe)
- ✅ Agent configuration is preserved
- ✅ Billing stops for the capacity SKU

---

## Resume

When you're ready to use the accelerator again:

### Resume via Makefile

```bash
make infra-resume
```

### Resume via Azure CLI

```bash
# Resume Fabric capacity
az fabric capacity resume \
  --resource-group rg-fabric-sales-agent \
  --capacity-name fabric-sales-agent-f2

# Verify it's running
az fabric capacity show \
  --resource-group rg-fabric-sales-agent \
  --capacity-name fabric-sales-agent-f2 \
  --query "properties.state" \
  --output tsv
# Expected output: Active
```

### Resume Sequence

1. Resume Fabric capacity (~1–2 min to become active)
2. Verify Data Agent responds in Fabric portal
3. If using M365 Direct Publish: agent should auto-reconnect (may take a few minutes)
4. If using Foundry: restart your orchestrator process

---

## Cost Optimization Tips

1. **Always pause Fabric capacity overnight and on weekends** — this alone can save 70%+ on Fabric costs.
2. **Use F2 if possible** — check if your tenant supports Data Agent on F2 before provisioning F64.
3. **Use GPT-4o-mini for simple queries** — route simple data questions to a cheaper model, reserve GPT-4o for complex multi-step queries.
4. **Set Azure budget alerts** — configure alerts at $300 and $500 thresholds to catch unexpected usage.
5. **Use reserved capacity** — if running long-term, Fabric reserved capacity (1-year) saves ~30% vs. pay-as-you-go.
6. **Monitor token usage** — use the Foundry portal's usage dashboard to track actual consumption.
