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
  -> quota-estimator MCP
  -> .xlsx, .html, .pdf

M365 Copilot / Teams
  -> Azure AI Foundry agent
  -> FabricIQPreviewTool
  -> WorkIQPreviewTool or get_account_activity mock
  -> generate_quota_estimation_report function tool
  -> .xlsx, .html, .pdf
```

## Architecture decisions

| Decision | Why it matters |
|---|---|
| Shared `src/agents/quota_estimator/` package | Keeps quota math and rendering consistent between CLI prototypes and Foundry production agents. |
| Fabric-first inputs | The estimator expects rows shaped like `SalesOrderHeader` joined to `SalesTerritory`, so it stays close to WWI source data. |
| Deterministic calculations | Demo results are repeatable and testable without an LLM deciding quota math. |
| Mock-safe WorkIQ | The demo uses synthetic M365 activity unless WorkIQ credentials are configured. No real WorkIQ API calls are required. |
| Real artifacts | Excel, HTML, and PDF outputs prove the workflow is more than a chat response. |

## Data flow

1. The user asks for a quota forecast report.
2. The agent queries Fabric for trailing historical sales rows with territory, order date, revenue, quantity, and
   category when available.
3. The agent gathers market context from `researcher-agent` or Copilot research.
4. The agent gathers WorkIQ activity. In demo mode this is realistic synthetic email and meeting activity.
5. The quota estimator groups rows by territory and category, calculates historical trend, applies market and
   engagement adjustments, and records methodology plus citations.
6. Renderers write:
   - `*_quota_estimate.xlsx` with Summary, Recommendations, Sales Detail, and Methodology sheets
   - `*_quota_estimate.html` with a complete browser-viewable report
   - `*_quota_estimate.pdf` with an executive summary and chart

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
Generate a quota forecast report for Tailspin Toys
```

The skill instructs Copilot CLI to query `wwi-sales-data`, call `researcher-agent`, use mock or synthetic WorkIQ
activity when needed, then call `quota-estimator.generate_quota_estimation_report`.

## Running from Foundry / M365 Copilot

The Foundry orchestrator in `src/orchestrator/foundry_agent.py` exposes:

| Tool | Purpose |
|---|---|
| `generate_quota_estimation_report` | Generates XLSX, HTML, and PDF artifacts from Fabric rows, research, and WorkIQ activity. |
| `forecast_quota` | Compatibility wrapper that returns the legacy structured forecast payload for older prompts and tests. |
| `get_account_activity` | Mock WorkIQ fallback when a WorkIQ connection is not configured. |

Agent instructions tell the model to use `FabricIQPreviewTool` first, then WorkIQ or the mock fallback, and finally
the quota report function.

## Validating artifacts

Run a local smoke test from the repo root:

```powershell
uv run python -c "from src.agents.quota_estimator.pipeline import demo_research_data, demo_sales_rows, demo_workiq_activity, generate_quota_estimation_report; print(generate_quota_estimation_report(customer_name='Tailspin Toys', sales_rows=demo_sales_rows(), research_data=demo_research_data('Tailspin Toys'), workiq_activity=demo_workiq_activity('Tailspin Toys'), output_dir='output/quota-smoke'))"
```

Open the generated workbook and confirm it has Summary, Recommendations, Sales Detail, and Methodology sheets. Open
the HTML file in a browser and the PDF in a reader. The generated files are written under `output/`, which is ignored
by git.
