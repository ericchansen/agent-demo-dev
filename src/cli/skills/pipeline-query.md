---
name: Query Sales Pipeline
description: >
  Query the Wide World Importers sales pipeline via Fabric Data Agent.
  Supports questions about customers, revenue, orders, pipeline coverage,
  quota attainment, and more.
---

# Query Sales Pipeline

## What this skill does

Sends a natural-language question to the **Fabric Data Agent**
(`wwi-sales-data` MCP server) and returns the answer. The Data Agent
translates your question into a SQL query against the Wide World Importers
lakehouse and returns structured results.

## Data sources available

- **`fact_Sale`** — completed invoiced sales (revenue, profit, tax)
- **`fact_Order`** — sales orders including open/unfulfilled pipeline
- **`fact_Purchase`** — purchase orders from suppliers (cost data)
- **`fact_Transaction`** — financial transactions and outstanding balances
- **`quota_Target`** — fiscal year quota targets by salesperson and territory
- **Dimensions** — Customer, Stock Item, City, Employee, Date, Supplier

## Supported question types

- **Top customers** — "What are our top 10 customers by revenue?"
- **Revenue trends** — "Show monthly revenue for the last 6 months."
- **Territory breakdown** — "Break down pipeline value by territory."
- **Open pipeline** — "What is our open pipeline by salesperson?"
- **Backorders** — "Show all backorders in the pipeline."
- **Pipeline coverage** — "What is the pipeline coverage ratio by rep?"
- **Quota attainment** — "What is quota attainment YTD for FY2016?"
- **Fiscal reporting** — "Show sales by fiscal quarter for FY2016."
- **Cost analysis** — "What is the gross margin by product?"
- **AR aging** — "Which customers have outstanding balances?"
- **Customer drill-down** — "Show all open deals for Tailspin Toys."

## Example invocations

```
What are our top 10 customers by revenue?
```

```
What is the open pipeline by salesperson? Only show unfulfilled orders.
```

```
What is the quota attainment for each salesperson in FY2016?
```

```
Show pipeline coverage ratio by territory — flag anything below 3x.
```

```
What is the gross margin on USB novelty items?
```

## Prerequisites

- `wwi-sales-data` MCP server configured with a valid Fabric Data Agent URL
  (see `src/cli/mcp-config.json`)
