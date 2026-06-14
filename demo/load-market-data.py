#!/usr/bin/env python3
"""Download and normalize SEC EDGAR financial data for the market-data demo path.

Downloads a recent SEC EDGAR Financial Statement Data Set (quarterly ZIP),
filters to a curated list of well-known companies, and normalizes US GAAP
tags into simple columns suitable for natural-language queries.

Source: SEC EDGAR (https://www.sec.gov/dera/data/financial-statement-data-sets.html)
License: Public domain (US government work product)

Usage:
    python demo/load-market-data.py
    python demo/load-market-data.py --output-dir demo/market-data/output
    python demo/load-market-data.py --quarter 2024q4
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

# SEC requires a descriptive User-Agent per their fair access policy.
# https://www.sec.gov/os/accessing-edgar-data
_USER_AGENT = "FabricSalesAgentAccelerator/0.1 (open-source demo; https://github.com/ericchansen/agent-demo)"

# Base URL for SEC EDGAR Financial Statement Data Sets (quarterly ZIPs).
_EDGAR_BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"

# GAAP tags we normalize into simple columns.
# Each key is the output column name; values are SEC XBRL tags that map to it.
_GAAP_TAG_MAP: dict[str, list[str]] = {
    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "TotalRevenuesAndOtherIncome",
        "InterestAndDividendIncomeOperating",
        "FinancialServicesRevenue",
        "RegulatedAndUnregulatedOperatingRevenue",
        "RealEstateRevenueNet",
        "ElectricUtilityRevenue",
    ],
    "net_income": [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "ProfitLoss",
        "IncomeLossFromContinuingOperations",
    ],
    "total_assets": [
        "Assets",
        "AssetsCurrent",
    ],
}

# Reverse lookup: tag → (column_name, priority)
_TAG_PRIORITY: dict[str, tuple[str, int]] = {}
for _col, _tags in _GAAP_TAG_MAP.items():
    for _i, _tag in enumerate(_tags):
        _TAG_PRIORITY[_tag] = (_col, _i)

# All tags we care about, as a set for fast filtering.
_ALL_TAGS: frozenset[str] = frozenset(_TAG_PRIORITY.keys())


def _sizeof_fmt(num_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:,.1f} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:,.1f} TB"


def _load_company_list(csv_path: Path) -> dict[int, dict[str, str]]:
    """Load the curated company list CSV, returning {cik: {ticker, company_name, ...}}."""
    import pandas as pd

    df = pd.read_csv(csv_path, comment="#")
    df["cik"] = df["cik"].astype(int)
    return {
        int(row["cik"]): {
            "ticker": str(row["ticker"]),
            "company_name": str(row["company_name"]),
            "sic_code": str(row["sic_code"]),
            "industry": str(row["industry"]),
        }
        for _, row in df.iterrows()
    }


def _download_edgar_zip(quarter: str, *, retries: int = 3) -> bytes:
    """Download an SEC EDGAR quarterly ZIP, returning raw bytes."""
    url = f"{_EDGAR_BASE}/{quarter}.zip"
    print(f"  ↓ Downloading {url}")

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            print(f"    Attempt {attempt}/{retries} …", end="", flush=True)
            t0 = time.monotonic()
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                data = resp.read()
            elapsed = time.monotonic() - t0
            print(f" {_sizeof_fmt(len(data))} in {elapsed:.1f}s")
            return data
        except urllib.error.HTTPError as exc:
            last_error = exc
            print(f" HTTP {exc.code}")
            if exc.code == 404:
                raise RuntimeError(
                    f"Quarter '{quarter}' not found at SEC EDGAR. Try a recent quarter like '2024q4' or '2025q1'."
                ) from exc
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            print(f" error — {exc}")
        time.sleep(2**attempt)

    raise RuntimeError(f"Failed to download {url} after {retries} attempts") from last_error


def _parse_and_normalize(
    zip_data: bytes,
    company_map: dict[int, dict[str, str]],
) -> Any:
    """Extract sub.txt + num.txt from the ZIP, filter, and normalize."""
    import pandas as pd

    cik_set = set(company_map.keys())

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        # ---- sub.txt: submission metadata ----
        with zf.open("sub.txt") as f:
            sub = pd.read_csv(f, sep="\t", dtype=str, usecols=["adsh", "cik", "name", "form", "fy", "fp", "filed"])
        sub["cik"] = sub["cik"].astype(int)
        # Keep only 10-K and 10-Q filings from our company list.
        sub = sub[sub["cik"].isin(cik_set) & sub["form"].isin(["10-K", "10-Q"])]
        valid_adsh = set(sub["adsh"])
        print(f"    Submissions matched: {len(sub)} filings from {sub['cik'].nunique()} companies")

        # ---- num.txt: numeric facts ----
        with zf.open("num.txt") as f:
            num = pd.read_csv(
                f,
                sep="\t",
                dtype=str,
                usecols=["adsh", "tag", "version", "ddate", "qtrs", "uom", "value"],
            )
        # Filter to our submissions, tags, and USD values.
        num = num[num["adsh"].isin(valid_adsh) & num["tag"].isin(_ALL_TAGS) & (num["uom"] == "USD")]
        num["value"] = pd.to_numeric(num["value"], errors="coerce")
        num.dropna(subset=["value"], inplace=True)
        print(f"    Numeric facts matched: {len(num)} rows")

    # Merge submission metadata into numeric facts.
    merged = num.merge(sub[["adsh", "cik", "form", "fy", "fp", "filed"]], on="adsh", how="left")

    # Map GAAP tags → normalized columns and pick the best (highest-priority) tag per company/period/column.
    merged["column"] = merged["tag"].map(lambda t: _TAG_PRIORITY[t][0])
    merged["priority"] = merged["tag"].map(lambda t: _TAG_PRIORITY[t][1])

    # For each company + period + column, keep the tag with lowest priority number (= most preferred).
    merged.sort_values("priority", inplace=True)
    best = merged.drop_duplicates(subset=["cik", "ddate", "column"], keep="first")

    # Pivot so each row is (cik, period) with columns for revenue, net_income, total_assets.
    pivoted = best.pivot_table(
        index=["cik", "form", "fy", "fp", "ddate", "filed"],
        columns="column",
        values="value",
        aggfunc="first",
    ).reset_index()

    # Flatten multi-index columns.
    pivoted.columns = [c if isinstance(c, str) else c for c in pivoted.columns]

    # Add company metadata.
    pivoted["ticker"] = pivoted["cik"].map(lambda c: company_map.get(c, {}).get("ticker", ""))
    pivoted["company_name"] = pivoted["cik"].map(lambda c: company_map.get(c, {}).get("company_name", ""))
    pivoted["sic_code"] = pivoted["cik"].map(lambda c: company_map.get(c, {}).get("sic_code", ""))
    pivoted["industry"] = pivoted["cik"].map(lambda c: company_map.get(c, {}).get("industry", ""))

    # Rename for clarity.
    pivoted.rename(columns={"fy": "fiscal_year", "fp": "fiscal_period", "ddate": "period_end_date"}, inplace=True)

    # Ensure standard column set.
    for col in ("revenue", "net_income", "total_assets"):
        if col not in pivoted.columns:
            pivoted[col] = None

    # Select and order final columns.
    final_cols = [
        "cik",
        "ticker",
        "company_name",
        "sic_code",
        "industry",
        "form",
        "fiscal_year",
        "fiscal_period",
        "period_end_date",
        "filed",
        "revenue",
        "net_income",
        "total_assets",
    ]
    result = pivoted[[c for c in final_cols if c in pivoted.columns]].copy()
    result.sort_values(["company_name", "period_end_date"], inplace=True)

    print(f"    Normalized output: {len(result)} rows × {len(result.columns)} columns")
    return result


def load_market_data(quarter: str, output_dir: Path, company_csv: Path) -> list[Path]:
    """Main pipeline: download → filter → normalize → save."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load company list.
    print(f"\n{'─' * 60}")
    print("Market Data Loader — SEC EDGAR Financial Statements")
    print(f"{'─' * 60}")
    print(f"\nCompany list: {company_csv}")
    company_map = _load_company_list(company_csv)
    print(f"  {len(company_map)} companies loaded")

    # 2. Download EDGAR quarterly ZIP.
    print(f"\nQuarter: {quarter}")
    zip_data = _download_edgar_zip(quarter)

    # 3. Parse and normalize.
    print("\nProcessing:")
    df = _parse_and_normalize(zip_data, company_map)

    # 4. Save outputs.
    outputs: list[Path] = []

    parquet_path = output_dir / "company_financials.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"\n  ✓ {parquet_path} ({_sizeof_fmt(parquet_path.stat().st_size)})")
    outputs.append(parquet_path)

    csv_out = output_dir / "company_financials.csv"
    df.to_csv(csv_out, index=False)
    print(f"  ✓ {csv_out} ({_sizeof_fmt(csv_out.stat().st_size)})")
    outputs.append(csv_out)

    # 5. Copy companies.csv to output.
    dest_companies = output_dir / "companies.csv"
    if not dest_companies.exists() or dest_companies.resolve() != company_csv.resolve():
        shutil.copy2(company_csv, dest_companies)
        print(f"  ✓ {dest_companies} (copied)")
    outputs.append(dest_companies)

    # 6. Print summary and upload instructions.
    print(f"\n{'─' * 60}")
    print(f"Total files: {len(outputs)}")
    total_bytes = sum(p.stat().st_size for p in outputs)
    print(f"Total size: {_sizeof_fmt(total_bytes)}")
    _print_upload_instructions(output_dir)

    return outputs


def _print_upload_instructions(output_dir: Path) -> None:
    """Print manual upload instructions for Fabric Lakehouse."""
    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║  Upload to Microsoft Fabric Lakehouse                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Open your Fabric workspace in the browser.               ║
║  2. Create a new Lakehouse (e.g., 'MarketDataLH').           ║
║  3. Click 'Get data' → 'Upload files'.                       ║
║  4. Upload from: {str(output_dir.resolve()):<41s} ║
║     • company_financials.parquet  (SEC quarterly financials)  ║
║     • companies.csv               (company profiles)          ║
║  5. Right-click each file → 'Load to table'.                 ║
║  6. Create a Data Agent pointing at MarketDataLH.            ║
║  7. Enable MCP on the agent and copy the URL.                ║
║  8. Paste the URL into src/cli/mcp-config.json               ║
║     under the 'market-data' server entry.                    ║
║                                                              ║
║  See docs/data-paths.md for the full walkthrough.            ║
╚══════════════════════════════════════════════════════════════╝
"""
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and normalize SEC EDGAR data for the market-data demo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--quarter",
        default="2024q4",
        help="SEC EDGAR quarter to download (e.g., '2024q4', '2025q1'). Default: 2024q4",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "market-data" / "output",
        help="Directory to save output files. Default: demo/market-data/output",
    )
    parser.add_argument(
        "--company-list",
        type=Path,
        default=Path(__file__).parent / "market-data" / "companies.csv",
        help="Path to the curated company list CSV. Default: demo/market-data/companies.csv",
    )
    args = parser.parse_args()

    if not args.company_list.exists():
        print(f"Error: Company list not found: {args.company_list}", file=sys.stderr)
        sys.exit(1)

    try:
        load_market_data(args.quarter, args.output_dir, args.company_list)
    except RuntimeError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
