---
name: company-financials
description: Look up real public company financials from SEC EDGAR filings (revenue, income, assets)
---

# Company Financials Lookup

You are looking up real-world financial data for US public companies using SEC EDGAR filings.

## Steps

1. **Query company financials**: Use the `market-data` MCP server to retrieve SEC-filed financial data. The `company_financials` table has normalized revenue, net income, and total assets from 10-K (annual) and 10-Q (quarterly) filings. Examples:
   ```
   What was Microsoft's total revenue for the most recent fiscal year?
   ```
   ```
   Show Apple's quarterly revenue and net income for the last 4 quarters.
   ```
   ```
   What are NVIDIA's total assets from their most recent 10-K filing?
   ```

2. **Enrich with company profile**: Join with the `companies` table (on `cik`) to get industry context. Example:
   ```
   Show revenue and net income for all companies in the Software & Services industry.
   ```

3. **Calculate derived metrics**: For each company:
   - Net Margin % = (Net Income / Revenue) × 100
   - Asset Turnover = Revenue / Total Assets
   - YoY Growth = (Current Year Revenue − Prior Year Revenue) / Prior Year Revenue × 100

4. **Format the report**: Present as a markdown table with currency in millions:
   | Company | Ticker | FY | Revenue | Net Income | Margin % | Total Assets |
   |---------|--------|-----|---------|-----------|----------|-------------|
   | Name | TICK | 2024 | $X,XXXM | $Y,YYYM | Z.Z% | $A,AAAM |

5. **Add context**:
   - Cite the SEC filing type (10-K or 10-Q) and filing date
   - Note the fiscal period end date
   - Compare to industry peers if relevant
   - Flag any missing data points explicitly

6. **Source attribution**: Always include: "Source: SEC EDGAR, [filing type], filed [date]"

## Data Coverage

- ~50 major US public companies (Microsoft, Apple, Amazon, Google, etc.)
- Financial data from SEC 10-K and 10-Q filings
- Metrics: revenue, net_income, total_assets
- Join key: `cik` (SEC Central Index Key)
