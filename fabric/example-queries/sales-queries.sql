-- ============================================================
-- Wide World Importers — Few-Shot NL→SQL Examples
-- Target: Microsoft Fabric SQL analytics endpoint
-- ============================================================

-- Question: Who are our top 10 customers by total revenue?
SELECT TOP 10
    c.Customer,
    c.[Buying Group],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    COUNT(*) AS OrderLines
FROM fact_Sale f
JOIN dimension_Customer c ON f.[Customer Key] = c.[Customer Key]
GROUP BY c.Customer, c.[Buying Group]
ORDER BY TotalRevenue DESC;

-- Question: What are total sales by sales territory?
SELECT
    ci.[Sales Territory],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    COUNT(DISTINCT f.[Customer Key]) AS UniqueCustomers
FROM fact_Sale f
JOIN dimension_City ci ON f.[City Key] = ci.[City Key]
GROUP BY ci.[Sales Territory]
ORDER BY TotalRevenue DESC;

-- Question: Show me monthly sales trends for the last 12 months.
SELECT
    FORMAT(f.[Invoice Date Key], 'yyyy-MM') AS SalesMonth,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Quantity) AS TotalUnits,
    COUNT(DISTINCT f.[Customer Key]) AS ActiveCustomers
FROM fact_Sale f
WHERE f.[Invoice Date Key] >= DATEADD(MONTH, -12, GETDATE())
GROUP BY FORMAT(f.[Invoice Date Key], 'yyyy-MM')
ORDER BY SalesMonth;

-- Question: Which product categories generate the most revenue?
SELECT
    si.[Stock Item],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Quantity) AS TotalUnitsSold,
    ROUND(AVG(f.[Unit Price]), 2) AS AvgUnitPrice
FROM fact_Sale f
JOIN dimension_Stock_Item si ON f.[Stock Item Key] = si.[Stock Item Key]
GROUP BY si.[Stock Item]
ORDER BY TotalRevenue DESC;

-- Question: Who are the top 5 salespersons by revenue this year?
SELECT TOP 5
    e.Employee,
    e.[Preferred Name],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    COUNT(DISTINCT f.[Customer Key]) AS CustomersServed
FROM fact_Sale f
JOIN dimension_Employee e ON f.[Salesperson Key] = e.[Employee Key]
WHERE e.[Is Salesperson] = 1
  AND YEAR(f.[Invoice Date Key]) = YEAR(GETDATE())
GROUP BY e.Employee, e.[Preferred Name]
ORDER BY TotalRevenue DESC;

-- Question: How do this year's sales compare to last year by quarter?
WITH QuarterlySales AS (
    SELECT
        YEAR(f.[Invoice Date Key]) AS SalesYear,
        DATEPART(QUARTER, f.[Invoice Date Key]) AS SalesQuarter,
        SUM(f.[Total Including Tax]) AS TotalRevenue
    FROM fact_Sale f
    WHERE YEAR(f.[Invoice Date Key]) IN (YEAR(GETDATE()), YEAR(GETDATE()) - 1)
    GROUP BY YEAR(f.[Invoice Date Key]), DATEPART(QUARTER, f.[Invoice Date Key])
)
SELECT
    cy.SalesQuarter AS [Quarter],
    py.TotalRevenue AS LastYearRevenue,
    cy.TotalRevenue AS ThisYearRevenue,
    ROUND(cy.TotalRevenue - py.TotalRevenue, 2) AS Difference,
    ROUND((cy.TotalRevenue - py.TotalRevenue) / NULLIF(py.TotalRevenue, 0) * 100, 1) AS PctChange
FROM QuarterlySales cy
JOIN QuarterlySales py
    ON cy.SalesQuarter = py.SalesQuarter
    AND cy.SalesYear = YEAR(GETDATE())
    AND py.SalesYear = YEAR(GETDATE()) - 1
ORDER BY cy.SalesQuarter;

-- Question: What are the total sales for customer "Tailspin Toys (Head Office)"?
SELECT
    c.Customer,
    c.[Buying Group],
    c.Category,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    MIN(f.[Invoice Date Key]) AS FirstOrder,
    MAX(f.[Invoice Date Key]) AS LastOrder
FROM fact_Sale f
JOIN dimension_Customer c ON f.[Customer Key] = c.[Customer Key]
WHERE c.Customer = 'Tailspin Toys (Head Office)'
GROUP BY c.Customer, c.[Buying Group], c.Category;

-- Question: Which cities have the highest sales volume?
SELECT TOP 10
    ci.City,
    ci.[State Province],
    ci.[Sales Territory],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Quantity) AS TotalUnits
FROM fact_Sale f
JOIN dimension_City ci ON f.[City Key] = ci.[City Key]
GROUP BY ci.City, ci.[State Province], ci.[Sales Territory]
ORDER BY TotalRevenue DESC;

-- Question: What is the average order size by customer category?
SELECT
    c.Category,
    COUNT(*) AS OrderLines,
    ROUND(AVG(f.[Total Including Tax]), 2) AS AvgLineTotal,
    ROUND(SUM(f.[Total Including Tax]) / COUNT(DISTINCT f.[WWI Invoice ID]), 2) AS AvgInvoiceTotal,
    COUNT(DISTINCT c.[Customer Key]) AS CustomerCount
FROM fact_Sale f
JOIN dimension_Customer c ON f.[Customer Key] = c.[Customer Key]
GROUP BY c.Category
ORDER BY AvgInvoiceTotal DESC;

-- Question: Which customers had declining sales compared to the previous year?
WITH CustomerYearlySales AS (
    SELECT
        c.Customer,
        YEAR(f.[Invoice Date Key]) AS SalesYear,
        SUM(f.[Total Including Tax]) AS TotalRevenue
    FROM fact_Sale f
    JOIN dimension_Customer c ON f.[Customer Key] = c.[Customer Key]
    WHERE YEAR(f.[Invoice Date Key]) IN (YEAR(GETDATE()), YEAR(GETDATE()) - 1)
    GROUP BY c.Customer, YEAR(f.[Invoice Date Key])
)
SELECT
    cy.Customer,
    py.TotalRevenue AS LastYearRevenue,
    cy.TotalRevenue AS ThisYearRevenue,
    ROUND(cy.TotalRevenue - py.TotalRevenue, 2) AS Difference,
    ROUND((cy.TotalRevenue - py.TotalRevenue) / NULLIF(py.TotalRevenue, 0) * 100, 1) AS PctChange
FROM CustomerYearlySales cy
JOIN CustomerYearlySales py
    ON cy.Customer = py.Customer
    AND cy.SalesYear = YEAR(GETDATE())
    AND py.SalesYear = YEAR(GETDATE()) - 1
WHERE cy.TotalRevenue < py.TotalRevenue
ORDER BY Difference ASC;

-- Question: Show sales breakdown by buying group.
SELECT
    COALESCE(c.[Buying Group], 'No Buying Group') AS BuyingGroup,
    COUNT(DISTINCT c.[Customer Key]) AS CustomerCount,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    ROUND(SUM(f.Profit) / NULLIF(SUM(f.[Total Including Tax]), 0) * 100, 1) AS ProfitMarginPct
FROM fact_Sale f
JOIN dimension_Customer c ON f.[Customer Key] = c.[Customer Key]
GROUP BY c.[Buying Group]
ORDER BY TotalRevenue DESC;

-- Question: What were the sales for the Southeast territory last quarter?
SELECT
    ci.[Sales Territory],
    FORMAT(f.[Invoice Date Key], 'yyyy-MM') AS SalesMonth,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Quantity) AS TotalUnits
FROM fact_Sale f
JOIN dimension_City ci ON f.[City Key] = ci.[City Key]
WHERE ci.[Sales Territory] = 'Southeast'
  AND f.[Invoice Date Key] >= DATEADD(QUARTER, -1, DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()), 0))
  AND f.[Invoice Date Key] < DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()), 0)
GROUP BY ci.[Sales Territory], FORMAT(f.[Invoice Date Key], 'yyyy-MM')
ORDER BY SalesMonth;

-- Question: Which products have the lowest sales this year?
SELECT TOP 10
    si.[Stock Item],
    si.Brand,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Quantity) AS TotalUnits
FROM fact_Sale f
JOIN dimension_Stock_Item si ON f.[Stock Item Key] = si.[Stock Item Key]
WHERE YEAR(f.[Invoice Date Key]) = YEAR(GETDATE())
GROUP BY si.[Stock Item], si.Brand
ORDER BY TotalRevenue ASC;

-- Question: How many new customers did we acquire each month this year?
WITH FirstPurchase AS (
    SELECT
        f.[Customer Key],
        MIN(f.[Invoice Date Key]) AS FirstOrderDate
    FROM fact_Sale f
    GROUP BY f.[Customer Key]
)
SELECT
    FORMAT(fp.FirstOrderDate, 'yyyy-MM') AS AcquisitionMonth,
    COUNT(*) AS NewCustomers
FROM FirstPurchase fp
WHERE YEAR(fp.FirstOrderDate) = YEAR(GETDATE())
GROUP BY FORMAT(fp.FirstOrderDate, 'yyyy-MM')
ORDER BY AcquisitionMonth;

-- Question: What is the profit margin by sales territory?
SELECT
    ci.[Sales Territory],
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit,
    ROUND(SUM(f.Profit) / NULLIF(SUM(f.[Total Including Tax]), 0) * 100, 1) AS ProfitMarginPct,
    COUNT(DISTINCT f.[Customer Key]) AS UniqueCustomers
FROM fact_Sale f
JOIN dimension_City ci ON f.[City Key] = ci.[City Key]
GROUP BY ci.[Sales Territory]
ORDER BY ProfitMarginPct DESC;

-- ============================================================
-- Pipeline, Quota & Cost Queries
-- ============================================================

-- Question: What is our current open pipeline by salesperson?
SELECT
    e.Employee,
    e.[Preferred Name],
    COUNT(DISTINCT o.[WWI Order ID]) AS OpenOrders,
    SUM(o.[Total Including Tax]) AS PipelineValue,
    SUM(o.Quantity) AS TotalUnits
FROM fact_Order o
JOIN dimension_Employee e ON o.[Salesperson Key] = e.[Employee Key]
WHERE o.[Picked Date Key] IS NULL
  AND e.[Is Salesperson] = 1
GROUP BY e.Employee, e.[Preferred Name]
ORDER BY PipelineValue DESC;

-- Question: What is the pipeline coverage ratio by salesperson?
WITH OpenPipeline AS (
    SELECT
        o.[Salesperson Key],
        SUM(o.[Total Including Tax]) AS PipelineValue
    FROM fact_Order o
    WHERE o.[Picked Date Key] IS NULL
    GROUP BY o.[Salesperson Key]
),
AnnualQuota AS (
    SELECT
        [Salesperson Key],
        [Annual Quota]
    FROM quota_Target
    WHERE [Fiscal Year] = 2016
)
SELECT
    e.Employee,
    q.[Annual Quota],
    COALESCE(p.PipelineValue, 0) AS PipelineValue,
    ROUND(COALESCE(p.PipelineValue, 0) / NULLIF(q.[Annual Quota], 0), 2) AS CoverageRatio,
    CASE
        WHEN COALESCE(p.PipelineValue, 0) / NULLIF(q.[Annual Quota], 0) >= 3.0 THEN 'Healthy'
        WHEN COALESCE(p.PipelineValue, 0) / NULLIF(q.[Annual Quota], 0) >= 2.0 THEN 'At Risk'
        ELSE 'Critical'
    END AS CoverageStatus
FROM AnnualQuota q
JOIN dimension_Employee e ON q.[Salesperson Key] = e.[Employee Key]
LEFT JOIN OpenPipeline p ON q.[Salesperson Key] = p.[Salesperson Key]
WHERE e.[Is Salesperson] = 1
ORDER BY CoverageRatio ASC;

-- Question: What is the quota attainment YTD by salesperson for FY2016?
SELECT
    e.Employee,
    q.[Annual Quota],
    SUM(f.[Total Including Tax]) AS YTD_Revenue,
    ROUND(SUM(f.[Total Including Tax]) / NULLIF(q.[Annual Quota], 0) * 100, 1) AS AttainmentPct
FROM fact_Sale f
JOIN dimension_Employee e ON f.[Salesperson Key] = e.[Employee Key]
JOIN quota_Target q ON f.[Salesperson Key] = q.[Salesperson Key]
WHERE e.[Is Salesperson] = 1
  AND q.[Fiscal Year] = 2016
  AND YEAR(f.[Invoice Date Key]) = 2016
GROUP BY e.Employee, q.[Annual Quota]
ORDER BY AttainmentPct DESC;

-- Question: Show me all backorders in the pipeline.
SELECT
    o.[WWI Order ID],
    o.[WWI Backorder ID],
    c.Customer,
    si.[Stock Item],
    o.Quantity,
    o.[Total Including Tax],
    o.[Order Date Key]
FROM fact_Order o
JOIN dimension_Customer c ON o.[Customer Key] = c.[Customer Key]
JOIN dimension_Stock_Item si ON o.[Stock Item Key] = si.[Stock Item Key]
WHERE o.[WWI Backorder ID] IS NOT NULL
  AND o.[Picked Date Key] IS NULL
ORDER BY o.[Order Date Key];

-- Question: What are the total sales by fiscal year and quarter?
SELECT
    d.[Fiscal Year Label],
    CASE
        WHEN d.[Fiscal Month Number] BETWEEN 1 AND 3 THEN 'Q1'
        WHEN d.[Fiscal Month Number] BETWEEN 4 AND 6 THEN 'Q2'
        WHEN d.[Fiscal Month Number] BETWEEN 7 AND 9 THEN 'Q3'
        ELSE 'Q4'
    END AS FiscalQuarter,
    SUM(f.[Total Including Tax]) AS TotalRevenue,
    SUM(f.Profit) AS TotalProfit
FROM fact_Sale f
JOIN dimension_Date d ON f.[Invoice Date Key] = d.[Date]
GROUP BY d.[Fiscal Year Label],
    CASE
        WHEN d.[Fiscal Month Number] BETWEEN 1 AND 3 THEN 'Q1'
        WHEN d.[Fiscal Month Number] BETWEEN 4 AND 6 THEN 'Q2'
        WHEN d.[Fiscal Month Number] BETWEEN 7 AND 9 THEN 'Q3'
        ELSE 'Q4'
    END
ORDER BY d.[Fiscal Year Label], FiscalQuarter;

-- Question: What is the gross margin by product using purchase cost data?
SELECT
    si.[Stock Item],
    SUM(s.[Total Including Tax]) AS SalesRevenue,
    SUM(p.[Total Including Tax]) AS PurchaseCost,
    SUM(s.[Total Including Tax]) - SUM(p.[Total Including Tax]) AS GrossMargin,
    ROUND((SUM(s.[Total Including Tax]) - SUM(p.[Total Including Tax]))
        / NULLIF(SUM(s.[Total Including Tax]), 0) * 100, 1) AS MarginPct
FROM fact_Sale s
JOIN dimension_Stock_Item si ON s.[Stock Item Key] = si.[Stock Item Key]
LEFT JOIN (
    SELECT [Stock Item Key], SUM([Total Including Tax]) AS [Total Including Tax]
    FROM fact_Purchase
    GROUP BY [Stock Item Key]
) p ON s.[Stock Item Key] = p.[Stock Item Key]
GROUP BY si.[Stock Item]
ORDER BY GrossMargin DESC;

-- Question: Which customers have outstanding balances?
SELECT
    c.Customer,
    COUNT(*) AS OpenTransactions,
    SUM(t.[Outstanding Balance]) AS TotalOutstanding,
    MIN(t.[Date Key]) AS OldestTransaction,
    MAX(t.[Date Key]) AS NewestTransaction
FROM fact_Transaction t
JOIN dimension_Customer c ON t.[Customer Key] = c.[Customer Key]
WHERE t.[Outstanding Balance] > 0
  AND t.[Is Finalized] = 0
GROUP BY c.Customer
ORDER BY TotalOutstanding DESC;

-- Question: What are the top suppliers by purchase volume?
SELECT TOP 10
    s.Supplier,
    s.Category,
    COUNT(DISTINCT p.[WWI Purchase Order ID]) AS PurchaseOrders,
    SUM(p.[Total Including Tax]) AS TotalSpend,
    SUM(p.[Ordered Quantity]) AS TotalUnitsOrdered
FROM fact_Purchase p
JOIN dimension_Supplier s ON p.[Supplier Key] = s.[Supplier Key]
GROUP BY s.Supplier, s.Category
ORDER BY TotalSpend DESC;

-- Question: Show the order-to-invoice conversion funnel.
SELECT
    'Total Orders' AS Stage,
    COUNT(DISTINCT [WWI Order ID]) AS OrderCount,
    SUM([Total Including Tax]) AS TotalValue
FROM fact_Order
UNION ALL
SELECT
    'Picked (Fulfilled)' AS Stage,
    COUNT(DISTINCT [WWI Order ID]) AS OrderCount,
    SUM([Total Including Tax]) AS TotalValue
FROM fact_Order
WHERE [Picked Date Key] IS NOT NULL
UNION ALL
SELECT
    'Invoiced (Revenue)' AS Stage,
    COUNT(DISTINCT [WWI Invoice ID]) AS OrderCount,
    SUM([Total Including Tax]) AS TotalValue
FROM fact_Sale;
