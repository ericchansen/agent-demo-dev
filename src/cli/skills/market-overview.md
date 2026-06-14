---
name: market-overview
description: Industry and sector analysis using SIC codes — compare companies, rank by revenue, show sector trends
---

# Market Overview

You are generating an industry or sector overview using SEC EDGAR financial data.

## Steps

1. **Identify the industry**: Use the `market-data` MCP server to query the `companies` table by SIC code or industry name. Example:
   ```
   What companies are in the Software & Services industry? Show their SIC codes.
   ```
   ```
   List all industries represented in the companies table with company counts.
   ```

2. **Pull industry financials**: Query `company_financials` joined with `companies` for the target industry. Example:
   ```
   Show annual revenue for all companies in the Semiconductors industry, most recent fiscal year, sorted by revenue descending.
   ```

3. **Build the overview table**:
   | Rank | Company | Ticker | Revenue | Net Income | Margin % | Market Position |
   |------|---------|--------|---------|-----------|----------|-----------------|
   | 1 | Leader | TICK | $XXM | $YYM | Z% | Dominant |

4. **Sector trends**: Compare year-over-year growth rates across the sector:
   - Average sector revenue growth
   - Top growers vs. laggards
   - Revenue concentration (top 3 companies' share of total sector revenue)

5. **Cross-sector comparison** (if requested):
   ```
   Compare average revenue and margins across Software, Semiconductors, and Banking industries.
   ```

6. **Add insights**:
   - Identify the market leader and key challengers
   - Highlight fastest-growing companies in the sector
   - Note industry-specific factors (e.g., semiconductor cyclicality, banking assets vs. revenue)
   - Suggest follow-up queries for deeper analysis

7. **Source attribution**: Always include: "Source: SEC EDGAR financial statement data sets"

## SIC Code Reference

- **3674**: Semiconductors
- **7372**: Software & Services
- **6020/6021/6022**: Banking
- **5912**: Pharmaceuticals / Retail
- **3711**: Motor Vehicles
- **5331**: Retail — General Merchandise

See `companies.csv` for the full list of SIC codes and industry labels.
