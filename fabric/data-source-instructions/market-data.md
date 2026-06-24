# Market Data — Schema & Query Guide

This document describes the tables available in the **Market Data** Lakehouse,
sourced from the SEC EDGAR **company facts** (XBRL) REST API. The tables are
produced by the one-time loader `scripts/load_sec_edgar.py`.

## Tables

### `company_financials`

Multi-period financial time series from SEC 10-K (annual) and 10-Q (quarterly)
filings. One row per company per reporting period, spanning many years.

| Column           | Type    | Description |
|------------------|---------|-------------|
| `cik`            | int     | SEC Central Index Key (unique per company) |
| `ticker`         | string  | Stock ticker symbol (e.g., MSFT, AAPL) |
| `company_name`   | string  | Common company name |
| `sic_code`       | string  | Standard Industrial Classification code |
| `industry`       | string  | Human-readable industry label |
| `form`           | string  | Filing type: `10-K` (annual) or `10-Q` (quarterly) |
| `fiscal_year`    | string  | Calendar year of the SEC reporting frame (see note below) |
| `fiscal_period`  | string  | `FY` = full year, `Q1`–`Q4` = calendar quarters |
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

- Data is loaded from the SEC EDGAR `companyfacts` XBRL API, which returns the full
  filing history per company (not a single quarter).
- The loader keeps only SEC's canonical **frame** facts — deduplicated,
  restatement-resolved values aligned to calendar periods — so each
  `(company, period)` appears once.
- `fiscal_year` reflects SEC's calendar-aligned frame label. For companies whose
  fiscal year ends in December it equals their stated fiscal year; for off-calendar
  filers (e.g. Apple, Nike) the label may differ by one from the company's own FY
  naming. The authoritative period is always `period_end_date`.
- `filed` indicates when the value was submitted to the SEC; `period_end_date` is the
  actual end of the reporting period.
- Re-run `scripts/load_sec_edgar.py` to refresh with the latest filings.

## Known Limitations

- Only ~50 curated companies are included (see `companies.csv` for the full list)
- Revenue normalization maps multiple US GAAP tags to a single `revenue` column
  (including `RevenuesNetOfInterestExpense` for banks); some companies may report
  revenue under less-common tags that aren't mapped
- `total_assets` uses the `Assets` tag matched to each period end date
- Foreign private issuers (20-F filers) are not included
- Only USD-denominated values are included
