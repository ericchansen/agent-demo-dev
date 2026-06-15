---
sidebar_position: 7
title: Sample Datasets
---

# Sample Datasets

This accelerator ships with **two data paths**, each backed by its own Fabric Data Agent and Lakehouse. Together they demonstrate how an agent can combine internal business data with external market intelligence.

## Wide World Importers (WWI)

The [Wide World Importers (WWI)](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is) dataset is a Microsoft-maintained sample simulating a wholesale novelty goods company. It's the primary demo data for sales queries, forecasts, and reports throughout this workshop.

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

> 📖 [Wide World Importers sample databases](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is)

## Customizing for your scenario

The WWI dataset works well for sales demos. If you want to use your own data:

1. Load your tables into a Fabric Lakehouse
2. Update the Data Agent configuration to point to your tables
3. Add few-shot examples in `fabric/few-shot-examples.json` for your schema
4. Update the Data Agent instructions in `fabric/data-agent-instructions.md`

The rest of the accelerator (MCP servers, skills, report generator) works the same — only the underlying data changes.

## Market Data (SEC EDGAR)

The second data path provides external financial data from SEC EDGAR filings, enabling competitive intelligence and market research scenarios.

| Table | Description | Key columns |
|---|---|---|
| `company_filings` | Quarterly/annual SEC filings | CIK, CompanyName, FilingType, FilingDate |
| `financial_statements` | Extracted financial metrics | CIK, Period, Revenue, NetIncome, TotalAssets |

### Why two data paths?

Most real-world agents need both internal and external data. The dual-path architecture shows how to:
- Configure **separate Data Agents** with different instructions and few-shot examples
- Build **skills that combine both** — e.g., "compare our Tailspin Toys revenue against their SEC filings"
- Keep concerns separated while the agent orchestrates across them

## Further reading

- [Wide World Importers overview](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is)
- [WWI database schema](https://learn.microsoft.com/sql/samples/wide-world-importers-oltp-database-catalog)
- SEC EDGAR company facts API documentation (referenced without a direct link because sec.gov blocks automated link validation)
- [Wide World Importers sample databases](https://learn.microsoft.com/sql/samples/wide-world-importers-what-is)
- [Fabric Data Agent setup](https://learn.microsoft.com/en-us/fabric/data-science/how-to-create-data-agent)
