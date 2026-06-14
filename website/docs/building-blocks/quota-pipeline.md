---
sidebar_position: 5
title: Quota Estimation Pipeline
---

# Quota Estimation Pipeline

The quota pipeline turns Fabric sales history, market context, and WorkIQ activity signals into three concrete
artifacts: an Excel workbook for analysis, an HTML report for quick sharing, and a PDF brief for read-only review.
The same Python package powers both demo surfaces:

```text
Copilot CLI skill
  -> wwi-sales-data Fabric Data Agent MCP
  -> researcher-agent MCP
  -> synthetic or mock WorkIQ activity
  -> quota-estimator MCP (scenario: conservative | base | aggressive)
  -> .xlsx, .html, .pdf

M365 Copilot / Teams
  -> Azure AI Foundry agent
  -> FabricIQPreviewTool
  -> WorkIQPreviewTool or get_account_activity mock
  -> generate_quota_estimation_report function tool (scenario aware)
  -> .xlsx, .html, .pdf
```

## Golden demo prompts

Copy-paste prompts that reliably exercise the full pipeline. Each produces the same three artifacts;
only the surface and phrasing differ. Use these as a known-good script when rehearsing a demo.

| Surface | Prompt | What it proves |
|---|---|---|
| Copilot CLI | `Generate a base quota forecast report for Tailspin Toys` | End-to-end CLI → MCP → artifacts. |
| Copilot CLI | `Generate an aggressive quota forecast report for Wingtip Toys and summarize the upside vs. the base case` | Scenario comparison in one turn. |
| Foundry / M365 | `@WWISalesAgent Build a quota estimation report for Tailspin Toys using our trailing sales and current market trends` | Fabric query → research → function tool. |
| Foundry / M365 | `@WWISalesAgent Give me conservative, base, and aggressive quota targets for Contoso Ltd with the assumptions behind each` | All three scenarios + methodology. |
| Hosted agent (HTTP) | `POST /invoke {"input": "Generate a quota report for Tailspin Toys"}` | Container runtime returns artifact summary JSON. |

> **Tip:** The word the model keys on for scenarios is `conservative`, `base`, or `aggressive`. Omitting it
> defaults to `base`. Naming a customer that exists in the WWI dataset (Tailspin Toys, Wingtip Toys, Contoso Ltd)
> keeps the Fabric query grounded.


## Operator quickstart

This is the fastest path from "I have sales rows" to three artifacts on disk. Everything below is
copy-pasteable and runs against the shared `src/agents/quota_estimator/` package.

### 1. Shape your input rows

Each sales row is a flat JSON object. The estimator accepts several field aliases (see
[Customizing for another dataset](#customizing-for-another-dataset)), but the canonical WWI shape is:

| Field | Type | Required | Notes |
|---|---|---|---|
| `territory` | string | yes | Sales territory name. Rows are grouped by territory. |
| `category` | string | no | Product category. Omitted rows are grouped under `All Products`. |
| `order_date` | string (`YYYY-MM-DD`) | yes | ISO date. Used to split the trailing window into prior vs. recent halves for the trend. |
| `revenue` | number | yes | Order revenue in dollars. |
| `quantity` | number | no | Units sold. Defaults to `0` when absent. |

A runnable WWI sample (two territories, two categories, recent + prior orders so a trend can be computed):

```json
[
  { "territory": "Northwest", "category": "Novelty Items", "order_date": "2025-07-30", "revenue": 190000, "quantity": 410 },
  { "territory": "Northwest", "category": "Novelty Items", "order_date": "2026-05-05", "revenue": 260000, "quantity": 520 },
  { "territory": "Northwest", "category": "Toys",          "order_date": "2025-09-17", "revenue": 90000,  "quantity": 240 },
  { "territory": "Northwest", "category": "Toys",          "order_date": "2026-05-25", "revenue": 125000, "quantity": 300 },
  { "territory": "Southwest", "category": "Clothing",      "order_date": "2025-10-07", "revenue": 155000, "quantity": 350 },
  { "territory": "Southwest", "category": "Clothing",      "order_date": "2026-05-30", "revenue": 165000, "quantity": 360 }
]
```

`research_data` and `workiq_activity` are optional. When omitted, the estimator still produces a
forecast from sales trend alone; in demos use `demo_research_data(...)` and `demo_workiq_activity(...)`
to populate realistic market and engagement signals.

### 2. Invoke the generator

**Copilot CLI** (after wiring `src/cli/mcp-config.json`):

```text
Generate an aggressive quota forecast report for Tailspin Toys
```

**Foundry / M365 Copilot** — the agent calls the `generate_quota_estimation_report` function tool with:

```json
{
  "customer_name": "Tailspin Toys",
  "sales_rows": [ /* the rows above */ ],
  "scenario": "aggressive",
  "output_dir": "output/quota-estimates"
}
```

**Python (direct)** — also the CI smoke path:

```powershell
uv run python -c "from src.agents.quota_estimator.pipeline import demo_research_data, demo_sales_rows, demo_workiq_activity, generate_quota_estimation_report; print(generate_quota_estimation_report(customer_name='Tailspin Toys', sales_rows=demo_sales_rows(), research_data=demo_research_data('Tailspin Toys'), workiq_activity=demo_workiq_activity('Tailspin Toys'), scenario='aggressive', output_dir='output/quota-smoke'))"
```

### 3. Collect the artifacts

Files are named `<customer-slug>_<scenario>_quota_estimate.<ext>` and written to `output_dir`. For the
command above you get three files in `output/quota-smoke/`:

| Artifact | File | What to check |
|---|---|---|
| Excel | `tailspin_toys_aggressive_quota_estimate.xlsx` | Summary, Recommendations, Sales Detail, Methodology, and Assumptions sheets. |
| HTML | `tailspin_toys_aggressive_quota_estimate.html` | Browser-viewable report with an inline base64 chart (no external assets). |
| PDF | `tailspin_toys_aggressive_quota_estimate.pdf` | Executive summary plus chart for read-only sharing. |

The function returns a JSON-serializable dict whose `artifacts` field maps each format to its absolute
path:

```json
{
  "artifacts": {
    "xlsx": ".../tailspin_toys_aggressive_quota_estimate.xlsx",
    "html": ".../tailspin_toys_aggressive_quota_estimate.html",
    "pdf":  ".../tailspin_toys_aggressive_quota_estimate.pdf"
  }
}
```

Everything under `output/` is git-ignored. The same end-to-end path runs in CI via
`tests/unit/test_quota_estimator.py::test_end_to_end_demo_artifacts_smoke`.

## Architecture decisions

| Decision | Why it matters |
|---|---|
| Shared `src/agents/quota_estimator/` package | Keeps quota math and rendering consistent between CLI prototypes and Foundry production agents. |
| Fabric-first inputs | The estimator expects rows shaped like `SalesOrderHeader` joined to `SalesTerritory`, so it stays close to WWI source data. |
| Deterministic calculations | Demo results are repeatable and testable without an LLM deciding quota math. |
| Deterministic scenarios | `conservative`, `base`, and `aggressive` apply fixed growth deltas (-3%, 0%, +3%) so stakeholders can compare bounded outcomes without re-querying. |
| Mock-safe WorkIQ | The demo uses synthetic M365 activity unless WorkIQ credentials are configured. No real WorkIQ API calls are required. |
| Injectable dates | Demo sales and activity dates are generated relative to an `as_of` date (today by default) so demos always look current, while tests pin a fixed date for determinism. |
| Real artifacts | Excel, HTML (with an embedded base64 chart), and PDF outputs prove the workflow is more than a chat response. |

## Scenario modes

Every entry point accepts an optional `scenario` field:

| Scenario | Growth delta | Use it for |
|---|---|---|
| `conservative` | -3% | Floor planning and downside cases. |
| `base` (default) | 0% | The recommended, evidence-weighted forecast. |
| `aggressive` | +3% | Stretch targets and upside planning. |

The delta is added to the trend, market, and engagement signals before the final growth rate is clamped to a safe
range. Generating all three scenarios for the same inputs yields strictly increasing quota totals
(`conservative < base < aggressive`), which the unit tests assert. The chosen scenario is recorded in the artifact
file name, the Excel **Summary** and **Assumptions** sheets, the HTML header, and the PDF cover page.

## Data flow

1. The user asks for a quota forecast report and optionally names a scenario.
2. The agent queries Fabric for trailing historical sales rows with territory, order date, revenue, quantity, and
   category when available.
3. The agent gathers market context from `researcher-agent` or Copilot research.
4. The agent gathers WorkIQ activity. In demo mode this is realistic synthetic email and meeting activity.
5. The quota estimator groups rows by territory and category, calculates historical trend, applies market,
   engagement, and scenario adjustments, and records methodology plus citations.
6. Renderers write:
   - `*_<scenario>_quota_estimate.xlsx` with Summary, Recommendations, Sales Detail, Methodology, and Assumptions sheets
   - `*_<scenario>_quota_estimate.html` with a complete browser-viewable report and an embedded chart image
   - `*_<scenario>_quota_estimate.pdf` with an executive summary and chart

## Customizing for another dataset

The estimator accepts flexible field names, but every row should provide these concepts:

| Concept | Accepted examples |
|---|---|
| Territory | `territory`, `territory_name`, `SalesTerritory`, `TerritoryName` |
| Category | `category`, `product_category`, `ProductCategory`, `StockItemCategory` |
| Order date | `order_date`, `OrderDate`, `SalesOrderDate` |
| Revenue | `revenue`, `total_revenue`, `sales_amount`, `TotalDue`, `ExtendedPrice` |
| Quantity | `quantity`, `Quantity`, `QuantitySold` |

For a non-WWI model, update the Fabric Data Agent prompt or SQL so it returns these concepts. If your dataset does
not have product categories, omit the category field and the estimator will group those rows under `All Products`.

## Running from Copilot CLI

Configure the local MCP servers from `src/cli/mcp-config.json`, then invoke the skill:

```text
Generate an aggressive quota forecast report for Tailspin Toys
```

The skill instructs Copilot CLI to query `wwi-sales-data`, call `researcher-agent`, use mock or synthetic WorkIQ
activity when needed, then call `quota-estimator.generate_quota_estimation_report` with the requested scenario.

> **MCP configuration:** `src/cli/mcp-config.json` is the authoritative, fully documented server registry for the
> CLI surface. The workspace files `.github/mcp.json` and `.vscode/mcp.json` are kept in sync and list the same
> stdio servers (`researcher-agent`, `sharepoint-agent`, `report-generator`, `quota-estimator`) plus the
> `wwi-sales-data` HTTP endpoint, so the skill's referenced servers resolve in both VS Code and Copilot CLI.

> **WorkIQ fallback:** When no WorkIQ connection is configured the pipeline accepts synthetic activity from
> `demo_workiq_activity(...)`. It is clearly labelled `synthetic demo activity (WorkIQ credentials not configured)`
> in the report sources, and it still drives the engagement adjustment so the demo behaves like the production path.

## Running from Foundry / M365 Copilot

The Foundry orchestrator in `src/orchestrator/foundry_agent.py` exposes:

| Tool | Purpose |
|---|---|
| `generate_quota_estimation_report` | Generates XLSX, HTML, and PDF artifacts from Fabric rows, research, and WorkIQ activity. Accepts an optional `scenario`. |
| `forecast_quota` | Compatibility wrapper that returns the legacy structured forecast payload. Also accepts an optional `scenario`. |
| `get_account_activity` | Mock WorkIQ fallback when a WorkIQ connection is not configured. |

Agent instructions tell the model to use `FabricIQPreviewTool` first, then WorkIQ or the mock fallback, and finally
the quota report function.

## Validating artifacts

Run a local smoke test from the repo root:

```powershell
uv run python -c "from src.agents.quota_estimator.pipeline import demo_research_data, demo_sales_rows, demo_workiq_activity, generate_quota_estimation_report; print(generate_quota_estimation_report(customer_name='Tailspin Toys', sales_rows=demo_sales_rows(), research_data=demo_research_data('Tailspin Toys'), workiq_activity=demo_workiq_activity('Tailspin Toys'), scenario='aggressive', output_dir='output/quota-smoke'))"
```

Open the generated workbook and confirm it has Summary, Recommendations, Sales Detail, Methodology, and Assumptions
sheets. Open the HTML file in a browser (the chart is embedded inline) and the PDF in a reader. The generated files
are written under `output/`, which is ignored by git. The same end-to-end path is exercised in CI by
`tests/unit/test_quota_estimator.py::test_end_to_end_demo_artifacts_smoke`.

## Networking & public access

The Foundry-hosted path (and the `ai.azure.com` portal you use to publish the agent) is only reachable when the
underlying Azure resources allow public network access. The Bicep modules default `publicNetworkAccess` to
`'Disabled'` — safe for production behind Private Link — but that default blocks the portal from loading and the
hosted agent container from being managed during a demo.

For the dev environment, `infra/parameters/dev.bicepparam` overrides this:

```bicep
param publicNetworkAccess = 'Enabled'
```

This single parameter flows through `infra/main.bicep` to the AI Foundry hub
(`infra/modules/ai-foundry.bicep`), Cognitive Services (`infra/modules/cognitive-services.bicep`), and storage
(`infra/modules/storage.bicep`). When `Enabled`, each module also sets its `networkAcls.defaultAction` to `Allow`
so the portal, Foundry runtime, and hosted container all stay reachable.

| Environment | `publicNetworkAccess` | Portal / hosted agent reachable | Use |
|---|---|---|---|
| Production (default) | `Disabled` | No — Private Link only | Locked-down deployments |
| Dev (`dev.bicepparam`) | `Enabled` | Yes | Demos and rapid prototyping |

> **If the Foundry portal will not load** (`ai.azure.com` spins or 403s), confirm the hub still has public access
> enabled:
>
> ```powershell
> az resource show --ids "<hub-resource-id>" --query "properties.publicNetworkAccess" -o tsv
> ```
>
> It should return `Enabled` for the dev hub. Re-apply with
> `az deployment group create -g rg-fabric-agent-dev -f infra/main.bicep -p infra/parameters/dev.bicepparam` if it
> has drifted back to `Disabled` (for example, after a governance policy re-applied the production default).

