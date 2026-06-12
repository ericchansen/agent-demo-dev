---
name: pipeline-coverage
description: Analyze sales pipeline coverage by salesperson and territory, flagging at-risk reps
---

# Pipeline Coverage Analysis

You are analyzing the sales pipeline coverage for Wide World Importers, comparing open orders against quota targets.

## Steps

1. **Query open pipeline**: Use the `wwi-sales-data` MCP server to get open (unfulfilled) orders from `fact_Order` where `Picked Date Key` IS NULL, grouped by salesperson. Example query:
   ```
   What is the total open pipeline value by salesperson? Show only unfulfilled orders (where Picked Date Key is null), with the number of open orders and total value for each salesperson.
   ```

2. **Query quota targets**: Retrieve quota targets from `quota_Target` for the current fiscal year (FY2016 in the demo dataset). Example:
   ```
   What are the annual quota targets by salesperson for FY2016?
   ```

3. **Calculate coverage ratios**: For each salesperson:
   - Coverage Ratio = Open Pipeline Value / Annual Quota
   - Classify: ≥3x = Healthy, 2–3x = At Risk, <2x = Critical

4. **Format the report**: Present as a markdown table:
   | Salesperson | Annual Quota | Pipeline Value | Coverage Ratio | Status |
   |---|---|---|---|---|
   | Name | $X | $Y | Z.Zx | Healthy/At Risk/Critical |

5. **Add risk analysis**:
   - Flag any salesperson with <2x coverage as **Critical** with recommended actions
   - Note any backordered items (WWI Backorder ID IS NOT NULL) that may slip
   - Include total team pipeline coverage vs. total team quota

6. **Summary**: 2-3 sentence executive summary with the team's overall coverage health and top risks.
