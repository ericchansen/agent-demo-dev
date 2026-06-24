"""Unit tests for the SEC EDGAR market data loader (scripts/load_sec_edgar.py).

These tests exercise the loader's pure functions against synthetic ``companyfacts``
JSON — no network access and no third-party dependencies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_LOADER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "load_sec_edgar.py"


def _import_loader() -> Any:
    """Import the loader module from its file path."""
    spec = importlib.util.spec_from_file_location("load_sec_edgar", _LOADER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def loader() -> Any:
    """Load the SEC EDGAR loader module once per test module."""
    return _import_loader()


def _usd(facts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"units": {"USD": facts}}


@pytest.fixture
def microsoft_facts() -> dict[str, Any]:
    """Synthetic companyfacts: one annual + one quarter + one unframed revenue point."""
    return {
        "facts": {
            "us-gaap": {
                "Revenues": _usd(
                    [
                        {"frame": "CY2023", "end": "2023-12-31", "filed": "2024-01-30", "val": 211915000000},
                        {"frame": "CY2023Q3", "end": "2023-09-30", "filed": "2023-10-24", "val": 56517000000},
                        # No frame -> must be ignored (not a canonical period).
                        {"end": "2023-06-30", "filed": "2023-07-25", "val": 99999},
                    ]
                ),
                "NetIncomeLoss": _usd(
                    [
                        {"frame": "CY2023", "end": "2023-12-31", "filed": "2024-01-30", "val": 72361000000},
                    ]
                ),
                "Assets": _usd(
                    [
                        {"frame": "CY2023Q4I", "end": "2023-12-31", "filed": "2024-01-30", "val": 411976000000},
                    ]
                ),
            }
        }
    }


# --- Frame regexes -----------------------------------------------------------


def test_annual_frame_matches_calendar_year(loader: Any) -> None:
    m = loader.ANNUAL_FRAME.match("CY2024")
    assert m is not None and m.group(1) == "2024"
    assert loader.ANNUAL_FRAME.match("CY2024Q3") is None
    assert loader.ANNUAL_FRAME.match("CY2024Q4I") is None


def test_quarter_frame_matches_calendar_quarter(loader: Any) -> None:
    m = loader.QUARTER_FRAME.match("CY2024Q3")
    assert m is not None and m.group(1) == "2024" and m.group(2) == "3"
    assert loader.QUARTER_FRAME.match("CY2024") is None
    # Instant (assets) frames carry a trailing I and must not match a duration quarter.
    assert loader.QUARTER_FRAME.match("CY2024Q3I") is None


# --- Formatting helpers ------------------------------------------------------


def test_fmt_int(loader: Any) -> None:
    assert loader._fmt_int({"val": 211915000000}) == "211915000000"
    assert loader._fmt_int({"val": 1234.0}) == "1234"
    assert loader._fmt_int(None) == ""


def test_fmt_date(loader: Any) -> None:
    assert loader._fmt_date("2023-12-31") == "20231231"
    assert loader._fmt_date(None) == ""
    assert loader._fmt_date("") == ""


# --- Framed fact extraction --------------------------------------------------


def test_framed_usd_facts_only_returns_framed(loader: Any, microsoft_facts: dict[str, Any]) -> None:
    framed = loader._framed_usd_facts(microsoft_facts, loader.REVENUE_TAGS)
    assert set(framed) == {"CY2023", "CY2023Q3"}  # unframed point dropped
    assert framed["CY2023"]["val"] == 211915000000


def test_framed_usd_facts_earlier_tag_wins(loader: Any) -> None:
    """When two revenue tags supply the same frame, the earlier tag in the list wins."""
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": _usd(
                    [{"frame": "CY2023", "end": "2023-12-31", "filed": "2024-01-30", "val": 100}]
                ),
                "Revenues": _usd([{"frame": "CY2023", "end": "2023-12-31", "filed": "2024-01-30", "val": 999}]),
            }
        }
    }
    framed = loader._framed_usd_facts(facts, loader.REVENUE_TAGS)
    assert framed["CY2023"]["val"] == 100


def test_framed_usd_facts_missing_tag(loader: Any) -> None:
    assert loader._framed_usd_facts({"facts": {"us-gaap": {}}}, loader.REVENUE_TAGS) == {}


# --- Row building ------------------------------------------------------------


def test_build_company_rows_annual_and_quarter(loader: Any, microsoft_facts: dict[str, Any]) -> None:
    rows = loader.build_company_rows(
        cik=789019,
        ticker="MSFT",
        name="Microsoft Corp",
        sic="7372",
        industry="Software & Services",
        facts=microsoft_facts,
    )
    by_period = {(r["form"], r["fiscal_period"]): r for r in rows}
    assert set(by_period) == {("10-K", "FY"), ("10-Q", "Q3")}

    annual = by_period[("10-K", "FY")]
    assert annual["fiscal_year"] == "2023"
    assert annual["period_end_date"] == "20231231"
    assert annual["revenue"] == "211915000000"
    assert annual["net_income"] == "72361000000"
    # Total assets matched to the period end date.
    assert annual["total_assets"] == "411976000000"
    # Carries through identity columns.
    assert annual["cik"] == 789019
    assert annual["ticker"] == "MSFT"
    assert annual["industry"] == "Software & Services"

    quarter = by_period[("10-Q", "Q3")]
    assert quarter["revenue"] == "56517000000"
    assert quarter["net_income"] == ""  # no CY2023Q3 net income supplied
    assert quarter["total_assets"] == ""  # no assets at the Q3 end date


def test_build_company_rows_bank_net_income_only(loader: Any) -> None:
    """Banks that omit a standard revenue tag still produce rows driven by net income."""
    facts = {
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": _usd(
                    [{"frame": "CY2023", "end": "2023-12-31", "filed": "2024-02-20", "val": 49552000000}]
                ),
            }
        }
    }
    rows = loader.build_company_rows(
        cik=19617, ticker="JPM", name="JPMorgan Chase", sic="6021", industry="Commercial Banking", facts=facts
    )
    assert len(rows) == 1
    assert rows[0]["form"] == "10-K"
    assert rows[0]["revenue"] == ""
    assert rows[0]["net_income"] == "49552000000"


def test_build_company_rows_sorted(loader: Any) -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": _usd(
                    [
                        {"frame": "CY2024", "end": "2024-12-31", "filed": "2025-01-30", "val": 2},
                        {"frame": "CY2023", "end": "2023-12-31", "filed": "2024-01-30", "val": 1},
                        {"frame": "CY2023Q1", "end": "2023-03-31", "filed": "2023-04-25", "val": 3},
                    ]
                ),
            }
        }
    }
    rows = loader.build_company_rows(cik=1, ticker="X", name="X", sic="0", industry="i", facts=facts)
    keys = [(r["form"], r["fiscal_year"], r["fiscal_period"]) for r in rows]
    assert keys == sorted(keys)
    # 10-K rows sort before 10-Q rows.
    assert keys[0][0] == "10-K"


def test_build_company_rows_empty(loader: Any) -> None:
    assert loader.build_company_rows(1, "X", "X", "0", "i", {"facts": {"us-gaap": {}}}) == []


# --- Curated universe + tag sets ---------------------------------------------


def test_curated_universe_is_unique_and_nonempty(loader: Any) -> None:
    tickers = [t for t, _ in loader.CURATED]
    assert len(tickers) >= 50
    assert len(tickers) == len(set(tickers))  # no duplicate tickers


def test_tag_sets(loader: Any) -> None:
    # Bank revenue concept must be covered so financials produce revenue rows.
    assert "RevenuesNetOfInterestExpense" in loader.REVENUE_TAGS
    assert loader.NET_INCOME_TAGS == ["NetIncomeLoss"]
    assert loader.ASSET_TAGS == ["Assets"]
