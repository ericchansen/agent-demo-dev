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

## Fact Table: `fact_Order`

Each row represents a single sales order line item. Orders not yet picked represent the **open pipeline**.

| Column | Type | Description |
|---|---|---|
| Order Key | int | Surrogate primary key |
| City Key | int | FK → dimension_City |
| Customer Key | int | FK → dimension_Customer |
| Stock Item Key | int | FK → dimension_Stock_Item |
| Order Date Key | date | Date the order was placed |
| Picked Date Key | date | Date order was picked (NULL = open/unfulfilled) |
| Salesperson Key | int | FK → dimension_Employee |
| Picker Key | int | FK → dimension_Employee (warehouse picker) |
| WWI Order ID | int | Source-system order number |
| WWI Backorder ID | int | Backorder reference (NULL = not backordered) |
| Description | nvarchar | Line-item description |
| Package | nvarchar | Package type |
| Quantity | int | Units ordered |
| Unit Price | decimal | Price per unit |
| Tax Rate | decimal | Tax percentage |
| Total Excluding Tax | decimal | Line total before tax |
| Tax Amount | decimal | Tax charged |
| Total Including Tax | decimal | Line total after tax |

## Fact Table: `fact_Purchase`

Each row represents a purchase order line from a supplier.

| Column | Type | Description |
|---|---|---|
| Purchase Key | int | Surrogate primary key |
| Date Key | date | Purchase date |
| Supplier Key | int | FK → dimension_Supplier |
| Stock Item Key | int | FK → dimension_Stock_Item |
| WWI Purchase Order ID | int | Source PO number |
| Ordered Outers | int | Outer packages ordered |
| Ordered Quantity | int | Units ordered |
| Received Outers | int | Packages received |
| Package | nvarchar | Package type |
| Is Order Finalized | bit | Whether the PO is closed |
| Total Excluding Tax | decimal | Cost before tax |
| Tax Amount | decimal | Tax |
| Total Including Tax | decimal | Total cost |

## Fact Table: `fact_Transaction`

Each row represents a financial transaction (invoice, payment, credit note).

| Column | Type | Description |
|---|---|---|
| Transaction Key | int | Surrogate primary key |
| Date Key | date | Transaction date |
| Customer Key | int | FK → dimension_Customer |
| Bill To Customer Key | int | FK → dimension_Customer |
| Payment Method Key | int | FK → dimension_Payment_Method |
| WWI Transaction ID | int | Source transaction number |
| WWI Invoice ID | int | Related invoice (nullable) |
| Description | nvarchar | Transaction description |
| Amount Excluding Tax | decimal | Amount before tax |
| Tax Amount | decimal | Tax |
| Amount Including Tax | decimal | Total |
| Outstanding Balance | decimal | Remaining balance |
| Is Finalized | bit | Whether settled |

## Fact Table: `fact_Movement`

Each row is a warehouse stock movement (receipt, issue, adjustment).

| Column | Type | Description |
|---|---|---|
| Movement Key | int | Surrogate primary key |
| Date Key | date | Movement date |
| Stock Item Key | int | FK → dimension_Stock_Item |
| Customer Key | int | FK → dimension_Customer (nullable) |
| Supplier Key | int | FK → dimension_Supplier (nullable) |
| Transaction Type Key | int | FK → dimension_Transaction_Type |
| WWI Stock Item Transaction ID | int | Source transaction ID |
| WWI Invoice ID | int | Related invoice (nullable) |
| WWI Purchase Order ID | int | Related PO (nullable) |
| Quantity | int | Movement quantity (positive = in, negative = out) |

## Fact Table: `fact_Stock_Holding`

Snapshot of current inventory levels.

| Column | Type | Description |
|---|---|---|
| Stock Holding Key | int | Surrogate primary key |
| Stock Item Key | int | FK → dimension_Stock_Item |
| Quantity On Hand | int | Current stock level |
| Bin Location | nvarchar | Warehouse bin |
| Last Stocktake Quantity | int | Last physical count |
| Last Cost Price | decimal | Last purchase price |
| Reorder Level | int | Minimum stock before reorder |
| Target Stock Level | int | Desired stock level |

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

### `dimension_Date`

Full calendar and fiscal period hierarchy.

| Column | Description |
|---|---|
| Date | Calendar date (PK) |
| Day Number | Day of month |
| Day | Day name (Monday, etc.) |
| Month | Month name |
| Short Month | Abbreviated month (Jan, Feb, etc.) |
| Calendar Month Number | 1-12 |
| Calendar Month Label | CY2016-Jan format |
| Calendar Year | Year number |
| Calendar Year Label | CY2016 format |
| Fiscal Month Number | Fiscal month (1-12) |
| Fiscal Month Label | FY2016-Jan format |
| Fiscal Year | Fiscal year number |
| Fiscal Year Label | FY2016 format |
| ISO Week Number | ISO week |

### `dimension_Supplier`

| Column | Description |
|---|---|
| Supplier Key | Surrogate key |
| WWI Supplier ID | Source-system ID |
| Supplier | Supplier name |
| Category | Supplier category |
| Primary Contact | Main contact person |
| Supplier Reference | Supplier's internal reference |
| Payment Days | Standard payment terms (days) |
| Postal Code | Supplier postal code |

### `dimension_Payment_Method`

| Column | Description |
|---|---|
| Payment Method Key | Surrogate key |
| WWI Payment Method ID | Source-system ID |
| Payment Method | Payment method name (Cash, Check, Credit Card, EFT) |

### `dimension_Transaction_Type`

| Column | Description |
|---|---|
| Transaction Type Key | Surrogate key |
| WWI Transaction Type ID | Source-system ID |
| Transaction Type | Type name (Invoice, Payment, Credit Note, etc.) |

### `quota_Target` (Synthetic)

Synthetic quota targets for the demo. Each row assigns a fiscal year quota to a salesperson in a territory.

| Column | Type | Description |
|---|---|---|
| Fiscal Year | int | Fiscal year (e.g., 2016) |
| Salesperson Key | int | FK → dimension_Employee |
| Employee | nvarchar | Salesperson name |
| Sales Territory | nvarchar | Territory name |
| Annual Quota | decimal | Full-year quota target |
| Q1 Quota | decimal | Q1 target |
| Q2 Quota | decimal | Q2 target |
| Q3 Quota | decimal | Q3 target |
| Q4 Quota | decimal | Q4 target |

## Relationships

```
fact_Sale.Customer Key       → dimension_Customer.Customer Key
fact_Sale.Bill To Customer Key → dimension_Customer.Customer Key
fact_Sale.Stock Item Key     → dimension_Stock_Item.Stock Item Key
fact_Sale.City Key           → dimension_City.City Key
fact_Sale.Salesperson Key    → dimension_Employee.Employee Key
fact_Sale.Invoice Date Key  → dimension_Date.Date
fact_Order.Customer Key        → dimension_Customer.Customer Key
fact_Order.Stock Item Key      → dimension_Stock_Item.Stock Item Key
fact_Order.City Key            → dimension_City.City Key
fact_Order.Salesperson Key     → dimension_Employee.Employee Key
fact_Order.Order Date Key      → dimension_Date.Date
fact_Purchase.Supplier Key     → dimension_Supplier.Supplier Key
fact_Purchase.Stock Item Key   → dimension_Stock_Item.Stock Item Key
fact_Purchase.Date Key         → dimension_Date.Date
fact_Transaction.Customer Key  → dimension_Customer.Customer Key
fact_Transaction.Payment Method Key → dimension_Payment_Method.Payment Method Key
fact_Transaction.Date Key      → dimension_Date.Date
fact_Movement.Stock Item Key   → dimension_Stock_Item.Stock Item Key
fact_Movement.Supplier Key     → dimension_Supplier.Supplier Key
fact_Movement.Customer Key     → dimension_Customer.Customer Key
fact_Movement.Date Key         → dimension_Date.Date
quota_Target.Salesperson Key   → dimension_Employee.Employee Key
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

### Open Pipeline / Unfulfilled Orders

Query `fact_Order` where `Picked Date Key IS NULL`. Join to `dimension_Customer` and `dimension_Employee` for pipeline by customer or salesperson.

### Pipeline Coverage Ratio

Join open orders from `fact_Order` (where `Picked Date Key IS NULL`) against trailing revenue from `fact_Sale`. Coverage = pipeline value / quota target. Healthy ratio is 3–4x.

### Quota Attainment

Join `fact_Sale` to `quota_Target` on `Salesperson Key` and fiscal year. Attainment % = actual revenue / quota × 100.

### Fiscal Year / Quarter Grouping

Join any fact table's date key to `dimension_Date`. Group by `Fiscal Year Label` and `Fiscal Month Number` for fiscal-aligned reporting.

### Cost of Goods / Margin Analysis

Join `fact_Sale` to `fact_Purchase` on `Stock Item Key` to compare revenue vs. cost. Gross margin = revenue − COGS.

### AR Aging / Outstanding Balances

Query `fact_Transaction` where `Outstanding Balance > 0` and `Is Finalized = 0`. Group by customer for AR aging report.
