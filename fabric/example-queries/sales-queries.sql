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
