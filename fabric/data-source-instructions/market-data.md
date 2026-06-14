# Market Data — Schema & Query Guide

This document describes the tables available in the **Market Data** Lakehouse,
sourced from SEC EDGAR Financial Statement Data Sets.

## Tables

### `company_financials`

Normalized quarterly financial data from SEC 10-K (annual) and 10-Q (quarterly) filings.

| Column           | Type    | Description |
|------------------|---------|-------------|
| `cik`            | int     | SEC Central Index Key (unique per company) |
| `ticker`         | string  | Stock ticker symbol (e.g., MSFT, AAPL) |
| `company_name`   | string  | Common company name |
| `sic_code`       | string  | Standard Industrial Classification code |
| `industry`       | string  | Human-readable industry label |
| `form`           | string  | Filing type: `10-K` (annual) or `10-Q` (quarterly) |
| `fiscal_year`    | string  | Fiscal year of the filing |
| `fiscal_period`  | string  | `FY` = full year, `Q1`/`Q2`/`Q3` = quarters |
| `period_end_date`| string  | End date of reporting period (YYYYMMDD) |
| `filed`          | string  | SEC filing date (YYYYMMDD) |
| `revenue`        | decimal | Total revenue in USD |
| `net_income`     | decimal | Net income (profit/loss) in USD |
| `total_assets`   | decimal | Total assets at period end in USD |

### `companies`

Company profile data for the curated list of ~50 major US public companies.

| Column         | Type   | Description |
|----------------|--------|-------------|
| `cik`          | int    | SEC Central Index Key (join key) |
| `ticker`       | string | Stock ticker symbol |
| `company_name` | string | Common company name |
| `sic_code`     | string | SIC industry code |
| `industry`     | string | Industry label from SIC code |

## Join Guidance

- **Primary key:** `cik` (integer, unique per company)
- **Join:** `company_financials.cik = companies.cik`
- Always join through `cik`, not `ticker` (tickers can change over time)

## Data Freshness

- Data is loaded from SEC EDGAR quarterly data sets
- Each load covers a single SEC quarter (e.g., `2024q4`)
- Filing dates in `filed` indicate when the data was submitted to the SEC
- The `period_end_date` indicates the actual reporting period

## Known Limitations

- Only ~50 curated companies are included (see `companies.csv` for the full list)
- Revenue normalization maps multiple US GAAP tags to a single `revenue` column;
  some companies may report revenue under less-common tags that aren't mapped
- `total_assets` may use `AssetsCurrent` if `Assets` isn't available
- Foreign private issuers (20-F filers) are not included
- Only USD-denominated values are included
