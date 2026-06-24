#!/usr/bin/env python3
"""Load real SEC EDGAR financials into CSVs for the Market Data Fabric Lakehouse.

This is a **one-time provisioning script**, not demo runtime. It pulls public-domain
data from the SEC EDGAR REST APIs (``companyfacts`` + ``submissions``) for a curated
set of ~50 major US public companies and emits two CSV files that match
``fabric/market-data-agent-config.json`` exactly:

    company_financials.csv
        cik,ticker,company_name,sic_code,industry,form,fiscal_year,
        fiscal_period,period_end_date,filed,revenue,net_income,total_assets
    companies.csv
        cik,ticker,company_name,sic_code,industry

Upload both to a Fabric Lakehouse, build the Market Data Data Agent over them, and
connect it to the Foundry project (see docs/setup-guide.md).

SEC fair-access policy requires a descriptive ``User-Agent`` and <=10 requests/sec:
https://www.sec.gov/os/accessing-edgar-data

Usage::

    python scripts/load_sec_edgar.py --user-agent "Your Name your.email@example.com"

The script uses only the Python standard library so it runs without the project venv.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

JSON = dict[str, Any]

# --- Curated company universe -------------------------------------------------
# (ticker, friendly industry label). The industry labels are intentionally curated
# so the example queries in fabric/example-queries/market-queries.sql return rows
# (e.g. "Software & Services", "Commercial Banking"). The real SIC code is pulled
# from SEC and stored alongside in sic_code.
CURATED: list[tuple[str, str]] = [
    # Software & Services
    ("MSFT", "Software & Services"),
    ("ORCL", "Software & Services"),
    ("CRM", "Software & Services"),
    ("ADBE", "Software & Services"),
    ("GOOGL", "Software & Services"),
    ("IBM", "Software & Services"),
    ("NOW", "Software & Services"),
    ("INTU", "Software & Services"),
    # Semiconductors & Hardware
    ("NVDA", "Semiconductors"),
    ("AMD", "Semiconductors"),
    ("INTC", "Semiconductors"),
    ("QCOM", "Semiconductors"),
    ("TXN", "Semiconductors"),
    ("AVGO", "Semiconductors"),
    ("AAPL", "Technology Hardware"),
    ("CSCO", "Technology Hardware"),
    ("DELL", "Technology Hardware"),
    # Internet & Media
    ("AMZN", "Internet Retail"),
    ("META", "Interactive Media"),
    ("NFLX", "Interactive Media"),
    ("DIS", "Media & Entertainment"),
    # Commercial Banking
    ("JPM", "Commercial Banking"),
    ("BAC", "Commercial Banking"),
    ("WFC", "Commercial Banking"),
    ("C", "Commercial Banking"),
    # Investment Services / Security Brokers
    ("GS", "Investment Services"),
    ("MS", "Investment Services"),
    ("SCHW", "Security Brokers"),
    ("BLK", "Investment Services"),
    ("AXP", "Investment Services"),
    # Healthcare & Pharma
    ("JNJ", "Pharmaceuticals"),
    ("PFE", "Pharmaceuticals"),
    ("MRK", "Pharmaceuticals"),
    ("ABBV", "Pharmaceuticals"),
    ("LLY", "Pharmaceuticals"),
    ("UNH", "Healthcare Services"),
    # Consumer
    ("WMT", "Retail"),
    ("COST", "Retail"),
    ("HD", "Retail"),
    ("TGT", "Retail"),
    ("PG", "Consumer Goods"),
    ("KO", "Consumer Goods"),
    ("PEP", "Consumer Goods"),
    ("MCD", "Restaurants"),
    ("SBUX", "Restaurants"),
    ("NKE", "Consumer Goods"),
    # Energy & Industrial
    ("XOM", "Energy"),
    ("CVX", "Energy"),
    ("GE", "Industrials"),
    ("BA", "Industrials"),
    ("CAT", "Industrials"),
    ("HON", "Industrials"),
    # Telecom & Auto
    ("VZ", "Telecommunications"),
    ("T", "Telecommunications"),
    ("TSLA", "Automotive"),
    ("F", "Automotive"),
]

# US GAAP revenue tags, tried in order of preference (last entries cover banks).
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "RevenuesNetOfInterestExpense",
]
NET_INCOME_TAGS = ["NetIncomeLoss"]
ASSET_TAGS = ["Assets"]

REQUEST_DELAY_SEC = 0.15  # ~6-7 req/s, safely under SEC's 10 req/s limit

# SEC "frame" labels mark canonical, deduplicated calendar periods:
#   CY2024      -> a full calendar-aligned annual period (duration)
#   CY2024Q3    -> a calendar quarter (duration)
#   CY2024Q3I   -> a calendar quarter end (instant, e.g. total assets)
ANNUAL_FRAME = re.compile(r"^CY(\d{4})$")
QUARTER_FRAME = re.compile(r"^CY(\d{4})Q([1-4])$")


def http_get_json(url: str, user_agent: str) -> JSON:
    """GET a JSON document from SEC EDGAR with the required User-Agent + retries."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip

                    raw = gzip.decompress(raw)
                result: JSON = json.loads(raw.decode("utf-8"))
                return result
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (403, 429, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Failed to GET {url}: {last_err}")


def load_cik_map(user_agent: str) -> dict[str, int]:
    """Return a {ticker: cik} map from SEC's master ticker file."""
    data = http_get_json("https://www.sec.gov/files/company_tickers.json", user_agent)
    out: dict[str, int] = {}
    for row in data.values():
        out[str(row["ticker"]).upper()] = int(row["cik_str"])
    return out


def _framed_usd_facts(facts: JSON, tags: list[str]) -> dict[str, JSON]:
    """Return {frame: fact} for canonical (framed) USD facts across ``tags``.

    SEC tags one fact per concept per calendar period with a ``frame`` label; these
    are already deduplicated and restatement-resolved. When several tags supply the
    same frame (e.g. a company switches revenue concepts over time) the earlier tag
    in ``tags`` wins.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    out: dict[str, JSON] = {}
    for tag in tags:
        node = us_gaap.get(tag)
        if not node:
            continue
        for fact in node.get("units", {}).get("USD", []):
            frame = fact.get("frame")
            if frame and frame not in out:
                out[frame] = fact
    return out


def _fmt_int(fact: JSON | None) -> str:
    return f"{fact['val']:.0f}" if fact else ""


def _fmt_date(value: str | None) -> str:
    return value.replace("-", "") if value else ""


def build_company_rows(cik: int, ticker: str, name: str, sic: str, industry: str, facts: JSON) -> list[JSON]:
    """Build one row per fiscal period from SEC canonical frames.

    Annual frames (``CYxxxx``) become 10-K / FY rows; quarter frames (``CYxxxxQn``)
    become 10-Q / Qn rows. Total assets are matched to the period end date.
    """
    revenue = _framed_usd_facts(facts, REVENUE_TAGS)
    net_income = _framed_usd_facts(facts, NET_INCOME_TAGS)
    assets_by_end = {fact["end"]: fact for fact in _framed_usd_facts(facts, ASSET_TAGS).values()}

    rows: list[JSON] = []
    # Union of all frames that carry revenue and/or net income, so banks that omit a
    # standard revenue tag still produce rows driven by net income.
    seen: set[str] = set()
    for frame in sorted(set(revenue) | set(net_income)):
        annual = ANNUAL_FRAME.match(frame)
        quarter = QUARTER_FRAME.match(frame)
        if annual:
            form, fiscal_year, fiscal_period = "10-K", annual.group(1), "FY"
        elif quarter:
            form, fiscal_year, fiscal_period = "10-Q", quarter.group(1), f"Q{quarter.group(2)}"
        else:
            continue
        if frame in seen:
            continue
        seen.add(frame)

        rev_fact = revenue.get(frame)
        ni_fact = net_income.get(frame)
        end = (rev_fact or ni_fact or {}).get("end")
        filed = (rev_fact or ni_fact or {}).get("filed")
        ast_fact = assets_by_end.get(end)
        rows.append(
            {
                "cik": cik,
                "ticker": ticker,
                "company_name": name,
                "sic_code": sic,
                "industry": industry,
                "form": form,
                "fiscal_year": fiscal_year,
                "fiscal_period": fiscal_period,
                "period_end_date": _fmt_date(end),
                "filed": _fmt_date(filed),
                "revenue": _fmt_int(rev_fact),
                "net_income": _fmt_int(ni_fact),
                "total_assets": _fmt_int(ast_fact),
            }
        )
    rows.sort(key=lambda r: (r["form"], r["fiscal_year"], r["fiscal_period"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load SEC EDGAR financials into Market Data CSVs.")
    parser.add_argument(
        "--user-agent",
        default=os.environ.get("SEC_USER_AGENT", ""),
        help="SEC-required User-Agent, e.g. 'Jane Doe jane@example.com'. Or set SEC_USER_AGENT.",
    )
    parser.add_argument(
        "--out",
        default="data/sec-edgar",
        help="Output directory for company_financials.csv + companies.csv (default: data/sec-edgar).",
    )
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N companies (for testing).")
    args = parser.parse_args(argv)

    if not args.user_agent or "@" not in args.user_agent:
        print(
            "ERROR: SEC requires a descriptive User-Agent containing a contact email.\n"
            "       Pass --user-agent 'Your Name you@example.com' or set SEC_USER_AGENT.\n"
            "       See https://www.sec.gov/os/accessing-edgar-data",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching SEC ticker -> CIK map ...")
    cik_map = load_cik_map(args.user_agent)
    time.sleep(REQUEST_DELAY_SEC)

    companies = CURATED[: args.limit] if args.limit else CURATED
    financial_rows: list[JSON] = []
    company_rows: list[JSON] = []

    for ticker, industry in companies:
        cik = cik_map.get(ticker.upper())
        if cik is None:
            print(f"  ! {ticker}: not found in SEC ticker map, skipping", file=sys.stderr)
            continue
        cik_padded = f"CIK{cik:010d}"
        try:
            submission = http_get_json(f"https://data.sec.gov/submissions/{cik_padded}.json", args.user_agent)
            time.sleep(REQUEST_DELAY_SEC)
            facts = http_get_json(f"https://data.sec.gov/api/xbrl/companyfacts/{cik_padded}.json", args.user_agent)
            time.sleep(REQUEST_DELAY_SEC)
        except RuntimeError as exc:
            print(f"  ! {ticker}: {exc}", file=sys.stderr)
            continue

        name = submission.get("name") or ticker
        sic = str(submission.get("sic") or "")
        rows = build_company_rows(cik, ticker, name, sic, industry, facts)
        if not rows:
            print(f"  ! {ticker}: no 10-K/10-Q financial rows extracted, skipping", file=sys.stderr)
            continue
        financial_rows.extend(rows)
        company_rows.append({"cik": cik, "ticker": ticker, "company_name": name, "sic_code": sic, "industry": industry})
        print(f"  + {ticker:6s} {name[:38]:38s} {len(rows):4d} rows")

    fin_path = out_dir / "company_financials.csv"
    co_path = out_dir / "companies.csv"
    with fin_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerows(financial_rows)
    with co_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["cik", "ticker", "company_name", "sic_code", "industry"])
        writer.writeheader()
        writer.writerows(company_rows)

    print(f"\nDone. {len(company_rows)} companies, {len(financial_rows)} financial rows.\n  {fin_path}\n  {co_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
