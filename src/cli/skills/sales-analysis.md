---
name: sales-analysis
description: |
  Deep sales analysis combining Fabric sales data, web market research, and
  M365 activity context to produce comprehensive quota/pipeline artifacts.
  Use when user asks for "full analysis", "deep dive", "sales review",
  "quota projection with research", or "account plan with data".
allowed-tools:
  - sales-data
  - report-generator
  - web_search
---

# Deep Sales Analysis

Produce a comprehensive, multi-source sales analysis for a customer, territory,
or sales rep. Combines structured data from Fabric, market research from the web,
and engagement signals from M365 (WorkIQ) into a cited, artifact-ready output.

---

## § 0 — Prerequisites

**Required MCP servers:**
- `sales-data` — Fabric Data Agent for structured sales queries

**Optional (enhance analysis if available):**
- `report-generator` — DOCX/PPTX artifact generation
- Web search (`/research` or `web_search` tool) — market research
- `workiq` — M365 engagement signals (use mock data if unavailable)

**Reference files (load on demand):**
- `schemas/sales-analysis-output.json` — JSON intermediate format schema
- `fabric/data-agent-config.json` — available tables and terminology

---

## § 1 — Identify Target

Parse the user's request to determine:
- **Customer name** (e.g., "Tailspin Toys") — maps to dimension_Customer
- **Territory** (e.g., "Southeast") — maps to dimension_City.[Sales Territory]
- **Sales rep** (e.g., "Hudson Onslow") — maps to dimension_Employee
- **Time range** — default to trailing 12 months + current FY projection
- **Output format** — Excel, HTML dashboard, DOCX, or markdown (ask if unclear)

If ambiguous, ask the user to clarify. Do NOT guess.

---

## § 2 — Gather Data (PARALLEL)

Execute these data-gathering steps in parallel where possible:

### 2a — Revenue History (Fabric)
```
Ask sales-data:
"Show monthly revenue (Total Including Tax) for [target] over the last 12 months,
grouped by month. Include row count per month."
```
→ Capture: monthly_trend array (month, revenue)

### 2b — Revenue by Category (Fabric)
```
Ask sales-data:
"What are [target]'s total sales by product category (Stock Item dimension)
for the current fiscal year? Show category, revenue, quantity, and percentage of total."
```
→ Capture: by_category array

### 2c — Top Customers (Fabric)
```
Ask sales-data:
"Who are the top 10 customers by revenue for [target/territory] in the current year?
Show customer name, revenue, quantity, and buying group."
```
→ Capture: pipeline array (repurposed for customer ranking)

### 2d — Territory Breakdown (Fabric)
```
Ask sales-data:
"Show revenue by sales territory for the current year and prior year.
Include year-over-year growth percentage."
```
→ Capture: territory comparison for summary

### 2e — Market Research (Web)
If web search is available:
```
Search for:
1. "[Customer/Industry] recent earnings quarterly results 2026"
2. "[Customer/Industry] market trends outlook"
3. "[Customer/Industry] expansion acquisitions news"
```
→ Capture: research.findings array (title, url, snippet, sales_implication)
→ Derive: research.tailwinds and research.headwinds arrays

If web search is NOT available, skip this step and note in metadata.data_sources
that market research was not included.

### 2f — Engagement Activity (WorkIQ)
If WorkIQ or mock activity data is available:
```
Query engagement for [target customer]:
- Meetings in last 30 days
- Emails in last 30 days
- Last interaction date
- Key contacts
```
→ Capture: activity object

If WorkIQ is NOT available, load mock engagement data from
`demo/mock-workiq-activity.json`. Look up the customer name in the
`customers` object and use the matching activity record.
If the customer is not in the mock data, populate activity with null values.

---

## § 3 — Sanity Check

Before computing derived metrics, verify:
1. Revenue totals are positive and reasonable (not zero, not negative)
2. Monthly trend has 10-12 data points (flag if sparse)
3. Category percentages sum to ~100% (±2% for rounding)
4. If any Fabric query returned an error, retry with a simpler query

If sanity checks fail, note the issue and proceed with available data.
Do NOT fabricate numbers.

---

## § 4 — Compute Derived Metrics

Calculate the following from gathered data:

### Quota Attainment
```
annual_target = prior_year_revenue × 1.10  (or use explicit target if provided)
ytd_actual = sum of current FY revenue
attainment_pct = ytd_actual / (annual_target × months_elapsed / 12) × 100
```

### Pipeline Coverage
```
open_pipeline = sum of pipeline[].value where stage != 'Closed'
remaining_quota = annual_target - ytd_actual
pipeline_coverage = open_pipeline / remaining_quota
```

### Run Rate Projection
```
days_elapsed = days since FY start
daily_rate = ytd_actual / days_elapsed
run_rate_projection = daily_rate × 365
```

### Risk Rating
```
Green: attainment ≥ 90% of pro-rata target AND pipeline_coverage ≥ 2.0
Yellow: attainment ≥ 70% OR pipeline_coverage ≥ 1.5
Red: attainment < 70% AND pipeline_coverage < 1.5
```

### Category Growth Rates
For each product category:
```
growth_rate = (current_fy_revenue - prior_fy_revenue) / prior_fy_revenue
projected_fy_revenue = current_fy_revenue × (1 + growth_rate)
```

### Relationship Strength (from WorkIQ)
```
Strong: ≥5 meetings + ≥10 emails in last 30 days
Active: ≥2 meetings OR ≥5 emails in last 30 days
Cooling: 1 meeting OR 2-4 emails in last 30 days
Stale: 0 meetings AND ≤1 email in last 30 days
```

---

## § 5 — Generate Recommendations

Produce 3-5 data-driven recommendations based on ALL gathered data:

- If pipeline_coverage < 2.0 → "Increase prospecting activity — pipeline coverage
  is below the 2× threshold needed to hit quota."
- If a category is declining → "Investigate declining [category] revenue —
  down [X]% YoY. Consider competitive displacement."
- If research shows expansion → "Capitalize on [customer]'s [expansion area] —
  recent [news item] suggests budget for [our product category]."
- If relationship_strength is Cooling/Stale → "Re-engage [customer] —
  no meetings in [N] days. Schedule executive check-in."
- If run_rate < annual_target → "Current run rate ($[X]M) projects below
  quota ($[Y]M). Close [Z] additional deals to bridge the gap."

Each recommendation must cite its data source.

---

## § 6 — Build JSON Intermediate

Assemble ALL gathered and computed data into the intermediate JSON format
defined in `schemas/sales-analysis-output.json`. This JSON is the input
for all artifact generators.

Save the JSON to a temp file: `sales-analysis-[customer]-[date].json`

---

## § 7 — Generate Output Artifact

Based on the user's requested format:

### Option A: Excel Workbook
```bash
node src/cli/report-scripts/sales-report-generator.cjs \
  sales-analysis-[customer]-[date].json \
  Sales_Analysis_[Customer]_[Date].xlsx
```

### Option B: HTML Dashboard
Read the template from `src/cli/report-scripts/dashboard-template.html`,
inject the JSON data, save as `Sales_Dashboard_[Customer]_[Date].html`.

### Option C: DOCX Report
Use the `report-generator` MCP server:
```
Call generate_report with:
  title: "Sales Analysis: [Customer]"
  customer_name: "[Customer]"
  pipeline_data: [from pipeline array]
  research_data: [from research object]
  forecast_data: [from quota object]
```

### Option D: Markdown (default)
Format the analysis as structured markdown tables and narrative directly
in the chat response. Include all citations inline.

---

## § 8 — Present Results

Regardless of output format, always provide:
1. **Executive summary** — 3-4 sentences covering the key findings
2. **Key risk** — the single most important thing the user should know
3. **Top recommendation** — the highest-priority action item
4. **Artifact link** — path to the generated file (if applicable)

---

## § Error Recovery

| Error | Recovery |
|-------|----------|
| Fabric query timeout | Retry with narrower date range (6 months instead of 12) |
| Fabric query returns 0 rows | Check customer name spelling, try partial match |
| Web search unavailable | Proceed without research section, note in output |
| WorkIQ unavailable | Use mock data if available, otherwise note as N/A |
| Report generator fails | Fall back to markdown output |
| Excel script fails | Fall back to CSV tables |

---

## Example Invocations

```
Run a deep analysis for Tailspin Toys and generate an Excel report
```

```
Full sales review for the Southeast territory — include market research
```

```
Quota projection for Hudson Onslow with engagement data — HTML dashboard
```

```
Deep dive on Wingtip Toys — markdown only, no file generation
```
