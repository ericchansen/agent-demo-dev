# Demo Script — Fabric Sales Agent Accelerator

End-to-end walkthrough showing multi-source sales analysis across surfaces.

---

## Pre-Demo Checklist

> Set `AZURE_SUBSCRIPTION_ID` to your subscription first (`export AZURE_SUBSCRIPTION_ID=<your-sub-id>`)
> so the capacity commands below target the right tenant.

```bash
# 1. Resume Fabric capacity (auto-pauses at midnight)
az fabric capacity resume \
  --capacity-name salesagentdemo \
  --resource-group rg-sales-agent-demo \
  --subscription "$AZURE_SUBSCRIPTION_ID"

# 2. Verify Fabric Data Agent is responding
# In Copilot CLI, run: @sales-data "What tables are available?"

# 3. Ensure Node.js + ExcelJS available (for Excel artifact)
cd src/cli/report-scripts && npm ls exceljs || npm install exceljs
```

---

## Demo 1: CLI Deep Sales Analysis (5 min)

**Story:** "I need a comprehensive analysis of Tailspin Toys to prepare
for tomorrow's QBR. I want data-driven insights from our sales warehouse,
market research, and engagement history — all combined into an Excel report."

### Step 1 — Invoke the sales analysis skill

```
Run a deep analysis for Tailspin Toys and generate an Excel report
```

**What happens behind the scenes:**
1. The `sales-analysis` skill instructs the CLI to gather data from multiple sources
2. Fabric Data Agent queries revenue trends, category breakdowns, top customers
3. Web research finds market news and competitive intelligence
4. Mock WorkIQ data provides engagement signals (meetings, emails, contacts)
5. Derived metrics are computed (quota attainment, pipeline coverage, risk rating)
6. ExcelJS script generates a 5-tab workbook

### Step 2 — Show the Excel output

Open the generated `.xlsx` file and walk through:
- **Summary** tab: KPI cards, executive summary
- **Pipeline** tab: Customer ranking with totals
- **Quota** tab: Category breakdown + monthly trend
- **Research** tab: Market findings with tailwinds/headwinds
- **Activity** tab: Engagement scores, key contacts

### Step 3 — Ask follow-up questions

```
What's the fastest-growing product category for Tailspin Toys?
```

```
Compare Tailspin Toys engagement to Contoso Ltd
```

---

## Demo 2: HTML Dashboard (2 min)

```
Create an HTML dashboard for the Southeast territory
```

Open the generated `.html` file in a browser — interactive charts,
responsive layout, no server needed.

---

## Demo 3: M365 Copilot (2 min)

**Story:** "The same data is available in M365 Copilot Chat for users
who prefer the Microsoft 365 experience."

1. Open M365 Copilot Chat (copilot.microsoft.com)
2. Select the published **Sales Agent**
3. Ask: "What are the top 5 customers by revenue this year?"
4. Ask: "Show monthly sales trend for the Southeast territory"

**Key point:** Same Fabric Data Agent, different surface. Zero code needed.

---

## Demo 4: Foundry Prompt Agent (2 min)

**Story:** "For production deployments, Azure AI Foundry provides a managed
agent runtime with additional tools."

Show in Foundry playground:
1. Ask: "Forecast quota for Tailspin Toys"
2. Ask: "Generate a report for Wingtip Toys with market research"

**Key point:** FunctionTools (quota forecast, web research, attainment
computation, report generation) extend beyond what Fabric alone provides.

---

## Talking Points

- **One data source, five surfaces** — same Fabric Data Agent powers CLI,
  M365, Foundry Prompt Agent, Hosted Agent, and future Cowork
- **No framework needed for CLI** — the LLM follows SKILL.md instructions
  to orchestrate tools, just like a developer would
- **JSON intermediate format** — all generators consume the same schema,
  making it easy to add PDF, PowerPoint, or any new format
- **Citations first-class** — every data point traces back to Fabric,
  web research, or WorkIQ
- **Cross-tenant solved** — stdio MCP proxy enables CLI access to Fabric
  workspaces in any tenant where the user has az CLI credentials

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Fabric query fails | Check capacity is resumed: `az fabric capacity show ...` |
| Proxy token error | Re-login: `az login --tenant MngEnvMCAP...` |
| Excel generation fails | `cd src/cli/report-scripts && npm install exceljs` |
| HTML dashboard empty | Ensure JSON data was saved to temp file before opening template |
| M365 agent not visible | Re-publish from Fabric portal → Share → Copilot |

---

## Post-Demo

```bash
# Pause Fabric capacity to avoid charges (~$270/month for F2)
az fabric capacity suspend \
  --capacity-name salesagentdemo \
  --resource-group rg-sales-agent-demo \
  --subscription "$AZURE_SUBSCRIPTION_ID"
```
