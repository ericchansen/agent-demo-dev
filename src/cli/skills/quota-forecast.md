---
name: quota-forecast
description: Generate FY quota estimation artifacts from sales, market research, and WorkIQ activity
---

# Quota Estimation Report Generator

You are generating a fiscal year quota estimation report for a sales customer. Produce real
artifacts, not only inline markdown.

## Steps

1. **Query sales data**: Use the `sales-data` MCP server to get the customer's trailing historical sales
   from `SalesOrderHeader` joined to `SalesTerritory`, broken down by territory and product category when the
   semantic model exposes category. Include at least territory, category, order date, revenue, and quantity.
   Example query:
   ```
   For [customer], return trailing 12-month sales rows from SalesOrderHeader joined to SalesTerritory.
   Include territory, product category, order date, total revenue, and quantity.
   ```

2. **Gather market context**: Use the external market-research agent (deployed separately from
   `ericchansen/market-research`) for a company financial forecast, or Copilot's own research. Pass its
   output through `quota_estimator.market_research_adapter.market_research_to_research_data` to get the
   `research_data` shape. If no research source is configured, accept a mock response and state that mock
   market context was used.

3. **Gather WorkIQ context**: Use the configured WorkIQ tool if present. If real WorkIQ credentials are not
   configured, use synthetic or mock activity with realistic recent emails/meetings and an engagement score.
   Do not attempt to call real WorkIQ APIs without credentials.

4. **Generate artifacts**: Call `quota-estimator.generate_quota_estimation_report` with:
   - `customer_name`
   - `sales_rows` from `sales-data`
   - `research_data` adapted from the market-research agent (or mock context)
   - `workiq_activity` from WorkIQ/mock activity
   - `scenario`: one of `conservative`, `base` (default), or `aggressive`. Infer it from the user's
     request (for example "stretch" or "upside" maps to `aggressive`, "downside" or "floor" maps to
     `conservative`); otherwise use `base`.
   - `formats`: `["xlsx", "html", "pdf"]`
5. **Return results**: Provide a short executive summary, the selected scenario, the total recommended quota, and the
   generated `.xlsx`, `.html`, and `.pdf` artifact paths returned by the quota estimator.
