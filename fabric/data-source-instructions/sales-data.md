# Sales Data Source Instructions

## Overview

The Wide World Importers data warehouse is hosted on a Microsoft Fabric SQL analytics endpoint. All tables use the `dbo` schema. The star schema centers on `fact_Sale` with four dimension tables joined by surrogate keys.

## Fact Table: `fact_Sale`

Each row represents a single invoice line item.

| Column                  | Type         | Description                              |
|------------------------|-------------|------------------------------------------|
| Sale Key               | int         | Surrogate primary key                    |
| City Key               | int         | FK → dimension_City                      |
| Customer Key           | int         | FK → dimension_Customer                  |
| Bill To Customer Key   | int         | FK → dimension_Customer (billing entity) |
| Stock Item Key         | int         | FK → dimension_Stock_Item                |
| Invoice Date Key       | date        | Date the invoice was raised              |
| Delivery Date Key      | date        | Date goods were delivered                |
| Salesperson Key        | int         | FK → dimension_Employee                  |
| WWI Invoice ID         | int         | Source-system invoice number              |
| Description            | nvarchar    | Line-item description                    |
| Package               | nvarchar    | Package type (Each, Pair, etc.)          |
| Quantity               | int         | Units sold                               |
| Unit Price             | decimal     | Price per unit                           |
| Tax Rate               | decimal     | Tax percentage applied                   |
| Total Excluding Tax    | decimal     | Line total before tax                    |
| Tax Amount             | decimal     | Tax charged                              |
| Total Including Tax    | decimal     | Line total after tax (primary revenue measure) |
| Profit                 | decimal     | Margin on the line item                  |

## Dimension Tables

### `dimension_Customer`

| Column            | Description                                     |
|------------------|-------------------------------------------------|
| Customer Key     | Surrogate key                                    |
| WWI Customer ID  | Source-system ID                                 |
| Customer         | Customer name                                    |
| Bill To Customer | Name of billing entity (may differ from Customer)|
| Category         | Customer category (Corporate, Gift Store, etc.)  |
| Buying Group     | Buying group name (Tailspin Toys, Wingtip Toys)  |
| Primary Contact  | Main contact person                              |
| Postal Code      | Customer postal code                             |

### `dimension_Stock_Item`

| Column           | Description                           |
|-----------------|---------------------------------------|
| Stock Item Key  | Surrogate key                          |
| Stock Item      | Product name                           |
| Color           | Product color                          |
| Selling Price   | Current list price                     |
| Tax Rate        | Applicable tax rate                    |
| Brand           | Brand name                             |
| Size            | Product size                           |
| Lead Time Days  | Days from order to delivery            |
| Is Chiller Stock| Whether the item requires refrigeration|

### `dimension_City`

| Column                     | Description                     |
|---------------------------|---------------------------------|
| City Key                  | Surrogate key                    |
| City                      | City name                        |
| State Province            | State or province                |
| Country                   | Country name                     |
| Continent                 | Continent                        |
| Sales Territory           | Sales region (Southeast, etc.)   |
| Latest Recorded Population| Most recent population figure    |

### `dimension_Employee`

| Column          | Description                          |
|----------------|--------------------------------------|
| Employee Key   | Surrogate key                         |
| Employee       | Full name                             |
| Preferred Name | Display name                          |
| Is Salesperson | Whether the employee is a salesperson |

## Relationships

```
fact_Sale.Customer Key       → dimension_Customer.Customer Key
fact_Sale.Bill To Customer Key → dimension_Customer.Customer Key
fact_Sale.Stock Item Key     → dimension_Stock_Item.Stock Item Key
fact_Sale.City Key           → dimension_City.City Key
fact_Sale.Salesperson Key    → dimension_Employee.Employee Key
```

## Common Query Patterns

### Top Customers by Revenue

Join `fact_Sale` to `dimension_Customer` on `Customer Key`. Aggregate `Total Including Tax`. Order descending, limit with `TOP`.

### Sales by Territory

Join `fact_Sale` → `dimension_City` on `City Key`. Group by `Sales Territory`. Sum revenue and profit.

### Monthly Trends

Use `YEAR(Invoice Date Key)` and `MONTH(Invoice Date Key)` (or `FORMAT(Invoice Date Key, 'yyyy-MM')`) to group sales over time.

### Product Category Analysis

Join `fact_Sale` → `dimension_Stock_Item` on `Stock Item Key`. Group by product name, color, or use string patterns to categorize.

### Salesperson Performance

Join `fact_Sale` → `dimension_Employee` on `Salesperson Key`. Filter `Is Salesperson = 1`. Aggregate by employee.

### Year-over-Year Comparison

Use CTEs or subqueries to compare the same month/quarter across years. Calculate absolute difference and percentage change.
