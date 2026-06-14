-- =============================================================================
-- Market Data — Example Queries
-- =============================================================================
-- These T-SQL examples work with the market-data Lakehouse tables:
--   company_financials  — normalized SEC 10-K/10-Q filings
--   companies           — company profile data
-- =============================================================================

-- 1. Single company revenue lookup
-- Find Microsoft's most recent annual revenue.
SELECT ticker, company_name, fiscal_year, revenue
FROM company_financials
WHERE ticker = 'MSFT' AND form = '10-K'
ORDER BY period_end_date DESC
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY;

-- 2. Compare revenue across companies
-- Side-by-side annual revenue for the big 3 cloud providers.
SELECT ticker, company_name, fiscal_year, revenue, net_income
FROM company_financials
WHERE ticker IN ('MSFT', 'AMZN', 'GOOGL') AND form = '10-K'
ORDER BY fiscal_year DESC, revenue DESC;

-- 3. Industry ranking by revenue
-- Top companies in Software & Services by annual revenue.
SELECT c.ticker, c.company_name, cf.fiscal_year, cf.revenue
FROM company_financials cf
JOIN companies c ON cf.cik = c.cik
WHERE c.industry = 'Software & Services' AND cf.form = '10-K'
ORDER BY cf.fiscal_year DESC, cf.revenue DESC;

-- 4. Year-over-year revenue growth
-- Calculate NVIDIA's annual revenue growth rate.
SELECT
    curr.ticker,
    curr.fiscal_year AS year,
    curr.revenue AS revenue,
    prev.revenue AS prev_revenue,
    CASE WHEN prev.revenue > 0
         THEN ROUND((curr.revenue - prev.revenue) / prev.revenue * 100, 1)
         ELSE NULL
    END AS growth_pct
FROM company_financials curr
LEFT JOIN company_financials prev
    ON curr.cik = prev.cik
    AND curr.form = prev.form
    AND CAST(curr.fiscal_year AS INT) = CAST(prev.fiscal_year AS INT) + 1
WHERE curr.ticker = 'NVDA' AND curr.form = '10-K'
ORDER BY curr.fiscal_year DESC;

-- 5. Net income margin comparison
-- Compare profitability across tech giants.
SELECT
    ticker,
    company_name,
    fiscal_year,
    revenue,
    net_income,
    ROUND(net_income * 100.0 / NULLIF(revenue, 0), 1) AS margin_pct
FROM company_financials
WHERE ticker IN ('MSFT', 'AAPL', 'GOOGL', 'META', 'AMZN')
    AND form = '10-K'
ORDER BY fiscal_year DESC, margin_pct DESC;

-- 6. Largest companies by total assets
-- Banking and financial services companies ranked by total assets.
SELECT c.ticker, c.company_name, cf.fiscal_year, cf.total_assets
FROM company_financials cf
JOIN companies c ON cf.cik = c.cik
WHERE c.industry IN ('Commercial Banking', 'Investment Services', 'Security Brokers')
    AND cf.form = '10-K'
ORDER BY cf.fiscal_year DESC, cf.total_assets DESC;

-- 7. Quarterly revenue trend
-- Show quarterly revenue trend for Apple over the last 4 quarters.
SELECT ticker, fiscal_year, fiscal_period, period_end_date, revenue
FROM company_financials
WHERE ticker = 'AAPL' AND form = '10-Q'
ORDER BY period_end_date DESC
OFFSET 0 ROWS FETCH NEXT 4 ROWS ONLY;
