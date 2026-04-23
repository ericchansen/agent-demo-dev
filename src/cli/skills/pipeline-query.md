---
name: Query Sales Pipeline
description: >
  Query the Wide World Importers sales pipeline via Fabric Data Agent.
  Supports questions about top customers, revenue trends, territory
  breakdown, and more.
---

# Query Sales Pipeline

## What this skill does

Sends a natural-language question to the **Fabric Data Agent**
(`wwi-sales-data` MCP server) and returns the answer. The Data Agent
translates your question into a SQL query against the Wide World Importers
lakehouse and returns structured results.

## Supported question types

- **Top customers** — "What are our top 10 customers by revenue?"
- **Revenue trends** — "Show monthly revenue for the last 6 months."
- **Territory breakdown** — "Break down pipeline value by territory."
- **Deal stage analysis** — "How many deals are in each stage?"
- **Close date forecasting** — "Which deals are expected to close this quarter?"
- **Customer drill-down** — "Show all open deals for Tailspin Toys."

## Example invocations

```
What are our top 10 customers by revenue?
```

```
Show pipeline value broken down by territory for Q3
```

```
Which deals over $100K are expected to close this month?
```

## Prerequisites

- `wwi-sales-data` MCP server configured with a valid Fabric Data Agent URL
  (see `src/cli/mcp-config.json`)
