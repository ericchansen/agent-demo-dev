---
sidebar_position: 7
title: WWI Dataset
---

# Wide World Importers Dataset

This accelerator uses the [Wide World Importers (WWI)](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is) sample dataset — a Microsoft-maintained dataset simulating a wholesale novelty goods company. It's the demo data for all sales queries, forecasts, and reports throughout this workshop.

## Why WWI?

- **No customer data** — it's entirely synthetic, safe for demos and public repos
- **Rich enough for real queries** — customers, orders, products, salespeople, territories
- **Microsoft-maintained** — well-documented, regularly updated
- **Already in Fabric** — available as a sample dataset in Fabric workspaces

## Schema overview

The Lakehouse contains six core tables:

| Table | Description | Key columns |
|---|---|---|
| `dimension_customer` | Customer companies | CustomerKey, Customer, Category, BuyingGroup |
| `dimension_stock_item` | Products/inventory | StockItemKey, StockItem, UnitPrice, Brand |
| `dimension_employee` | Salespeople | EmployeeKey, Employee, IsSalesperson |
| `dimension_city` | Geography/territories | CityKey, City, StateProvince, Country |
| `dimension_date` | Calendar/fiscal dates | Date, FiscalYear, FiscalMonthNumber |
| `fact_sale` | Sales transactions | SaleKey, CustomerKey, StockItemKey, Quantity, TotalIncludingTax |

## Sample queries

These are the kinds of questions your agent can answer once connected to the Data Agent:

| Question | What it queries |
|---|---|
| "What were Tailspin Toys' total sales last quarter?" | `fact_sale` joined with `dimension_customer` and `dimension_date` |
| "Which product category had the highest revenue?" | `fact_sale` joined with `dimension_stock_item` |
| "Show me sales by territory for FY26" | `fact_sale` joined with `dimension_city` and `dimension_date` |
| "Who are our top 10 customers by revenue?" | `fact_sale` grouped by `dimension_customer` |
| "Compare Q2 vs Q3 sales for Tailspin Toys" | `fact_sale` with date-range filters |

## Loading the data

The WWI sample data is available in Fabric workspaces:

1. Open your Fabric workspace
2. Create a new Lakehouse
3. Use the "Load sample data" option → select Wide World Importers
4. Tables appear automatically in the Lakehouse

> 📖 [Load sample data in Fabric](https://learn.microsoft.com/fabric/data-engineering/lakehouse-sample-data)

## Customizing for your scenario

The WWI dataset works well for sales demos. If you want to use your own data:

1. Load your tables into a Fabric Lakehouse
2. Update the Data Agent configuration to point to your tables
3. Add few-shot examples in `fabric/few-shot-examples.json` for your schema
4. Update the Data Agent instructions in `fabric/data-agent-instructions.md`

The rest of the accelerator (MCP servers, skills, report generator) works the same — only the underlying data changes.

## Further reading

- [Wide World Importers overview](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is)
- [WWI database schema](https://learn.microsoft.com/sql/samples/wide-world-importers-oltp-database-catalog)
- [Fabric Lakehouse sample data](https://learn.microsoft.com/fabric/data-engineering/lakehouse-sample-data)
- [Fabric Data Agent setup](https://learn.microsoft.com/fabric/data-engineering/data-agent-create)
