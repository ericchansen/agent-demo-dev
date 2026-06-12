---
name: quota-forecast
description: Generate an FY quota forecast for a customer based on trailing sales data and pipeline
---

# Quota Forecast Generator

You are generating a fiscal year quota forecast for a Wide World Importers customer.

## Steps

1. **Query sales data**: Use the `wwi-sales-data` MCP server to get the customer's trailing 12-month sales broken down by product category. Use `dimension_Date` for fiscal year alignment. Example query:
   ```
   What were [customer]'s total sales by product category (StockItem dimension) for fiscal year 2015 and 2016? Show each category with total revenue and quantity, broken down by fiscal year using dimension_Date.
   ```

2. **Query open pipeline**: Check for open orders from `fact_Order`:
   ```
   What open orders (Picked Date Key IS NULL) exist for [customer]? Show product category, quantity, and value.
   ```

3. **Calculate projections**: For each product category:
   - Calculate year-over-year growth rate from historical data
   - Apply growth rate (default 10-15% for growing categories, 5% for stable, 0% for declining)
   - Add open pipeline value as committed upside
   - Project the next fiscal year revenue

4. **Format the forecast**: Present as a markdown table:
   | Product Category | FY2015 Revenue | FY2016 Revenue | YoY Growth | Open Pipeline | Projected FY2017 |
   |---|---|---|---|---|---|
   | Category 1 | $X | $Y | Z% | $P | $F |
   | ... | ... | ... | ... | ... | ... |
   | **Total** | **$X** | **$Y** | **Z%** | **$P** | **$F** |

5. **Add insights**:
   - Highlight the top 3 growth categories
   - Flag any declining categories with recommendations
   - Note pipeline upside vs. organic growth contribution
   - Include methodology note: "Based on fiscal-year-aligned sales data from the WWI data warehouse with pipeline overlay from open orders"

6. **Summary**: Provide a 2-3 sentence executive summary suitable for a QBR deck.
