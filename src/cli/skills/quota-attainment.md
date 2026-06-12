---
name: quota-attainment
description: Calculate YTD and quarterly quota attainment by salesperson with burn-down analysis
---

# Quota Attainment Report

You are generating a quota attainment report for Wide World Importers, showing actual sales vs. quota targets.

## Steps

1. **Query YTD actuals**: Use the `wwi-sales-data` MCP server to get actual invoiced revenue from `fact_Sale` for the fiscal year, grouped by salesperson. Example:
   ```
   What are the total invoiced sales by salesperson for fiscal year 2016? Break down by fiscal quarter using the dimension_Date table.
   ```

2. **Query quota targets**: Retrieve the annual and quarterly quotas from `quota_Target`. Example:
   ```
   Show all quota targets for FY2016 with annual and quarterly breakdowns.
   ```

3. **Calculate attainment**: For each salesperson:
   - YTD Attainment % = (YTD Revenue / Annual Quota) × 100
   - Quarterly Attainment % = (Quarter Revenue / Quarter Quota) × 100
   - Remaining Quota = Annual Quota − YTD Revenue
   - Required Run Rate = Remaining Quota / Remaining Months

4. **Format the report**: Present as a markdown table:
   | Salesperson | Territory | Annual Quota | YTD Revenue | Attainment % | Remaining | Run Rate Needed |
   |---|---|---|---|---|---|---|
   | Name | Territory | $X | $Y | Z% | $R | $M/month |

5. **Quarterly detail** (expandable):
   | Salesperson | Q1 Quota | Q1 Actual | Q1 % | Q2 Quota | Q2 Actual | Q2 % | ... |
   |---|---|---|---|---|---|---|---|

6. **Add insights**:
   - Highlight top 3 performers by attainment %
   - Flag anyone below 80% of expected pace (YTD% < month/12 × 100)
   - Compare current trajectory vs. full-year target
   - If pipeline data is available, combine with coverage analysis for a complete picture

7. **Summary**: Executive summary with team attainment %, notable over/under performers, and recommended actions.
