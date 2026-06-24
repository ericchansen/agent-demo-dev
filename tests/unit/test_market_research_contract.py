"""Contract test: market-research output feeds the quota estimator.

The external ``ericchansen/market-research`` agent and the internal quota
estimator were built independently and use different schemas. This test pins
the adapter that bridges them so the multi-agent pipeline stays demoable and
regressions in either contract are caught offline.
"""

from __future__ import annotations

from src.agents.quota_estimator.market_research_adapter import (
    market_research_to_research_data,
)
from src.agents.quota_estimator.pipeline import build_quota_estimate


def _full_response() -> dict[str, object]:
    """A representative market-research ``FullResponse`` payload.

    Mirrors the schema in ericchansen/market-research ``src/schemas.py``
    (company / ticker / sector / data_sources / historical / prediction).
    Latest historical revenue is 1000; predicted base revenue is 1080, so the
    implied growth rate is 8%.
    """
    return {
        "company": "Tailspin Toys",
        "ticker": "TSPN",
        "sector": "Consumer Discretionary",
        "data_sources": {
            "financial": "SEC EDGAR 10-K filings",
            "store_count": "Company investor relations",
        },
        "historical": [
            {"fiscal_year": 2023, "revenue_usd_millions": 900},
            {"fiscal_year": 2024, "revenue_usd_millions": 1000},
        ],
        "prediction": {
            "fiscal_year": 2025,
            "revenue_usd_millions": {"bear": 1020, "base": 1080, "bull": 1150},
            "confidence": "medium",
            "methodology_summary": "Trend extrapolation with sector demand signals.",
            "analyst_consensus": {"source": "Aggregated sell-side estimates"},
        },
    }


def _sales_rows() -> list[dict[str, object]]:
    return [
        {
            "territory": "Northwest",
            "category": "Novelty Items",
            "order_date": "2025-07-01",
            "revenue": 100000,
            "quantity": 200,
        },
        {
            "territory": "Northwest",
            "category": "Novelty Items",
            "order_date": "2026-02-01",
            "revenue": 130000,
            "quantity": 240,
        },
    ]


def test_adapter_produces_quota_estimator_research_shape() -> None:
    research = market_research_to_research_data(_full_response())

    assert research["company_name"] == "Tailspin Toys"
    assert research["growth_rate"] == 0.08
    assert research["key_metrics"] == {"revenue_yoy_growth": 0.08}
    assert "8.0% revenue growth" in research["summary"]
    assert any(article["source"] == "SEC EDGAR 10-K filings" for article in research["articles"])


def test_adapter_output_drives_market_adjustment() -> None:
    research = market_research_to_research_data(_full_response())

    estimate = build_quota_estimate(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=research,
    )

    # 8% predicted growth -> growth_rate_hint 0.08 -> market_adjustment 0.08/4 = 0.02.
    assert estimate.research_context.growth_rate_hint == 0.08
    assert all(rec.market_adjustment == 0.02 for rec in estimate.recommendations)
    assert any("SEC EDGAR 10-K filings" in citation for citation in estimate.citations)


def test_adapter_degrades_without_prediction() -> None:
    payload = _full_response()
    del payload["prediction"]

    research = market_research_to_research_data(payload)

    assert "growth_rate" not in research
    assert research["company_name"] == "Tailspin Toys"

    estimate = build_quota_estimate(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=research,
    )
    # No derivable growth rate -> market adjustment falls back to zero.
    assert estimate.research_context.growth_rate_hint is None
    assert all(rec.market_adjustment == 0.0 for rec in estimate.recommendations)
