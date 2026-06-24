"""Adapter that maps market-research output into quota-estimator research_data.

The external `ericchansen/market-research` agent emits a structured financial
forecast (`FullResponse`: company/ticker/historical/prediction). The quota
estimator expects a lighter `research_data` shape (summary / growth_rate /
key_metrics / articles). This module is the thin glue that lets the external
research agent feed the internal quota pipeline so the demo behaves like one
multi-agent workflow instead of two disconnected services.

Keeping the mapping here (deterministic, no I/O) means it is unit-testable
without standing up the live market-research service.
"""

from __future__ import annotations

from collections.abc import Mapping


def _latest_historical_revenue(historical: object) -> float | None:
    """Return the revenue of the most recent fiscal year with a revenue value."""
    if not isinstance(historical, (list, tuple)):
        return None
    best_year: int | None = None
    best_revenue: float | None = None
    for entry in historical:
        if not isinstance(entry, Mapping):
            continue
        revenue = entry.get("revenue_usd_millions")
        year = entry.get("fiscal_year")
        if not isinstance(revenue, (int, float)) or not isinstance(year, int):
            continue
        if best_year is None or year > best_year:
            best_year = year
            best_revenue = float(revenue)
    return best_revenue


def _predicted_base_revenue(prediction: object) -> float | None:
    if not isinstance(prediction, Mapping):
        return None
    revenue_range = prediction.get("revenue_usd_millions")
    if not isinstance(revenue_range, Mapping):
        return None
    base = revenue_range.get("base")
    return float(base) if isinstance(base, (int, float)) else None


def market_research_to_research_data(full_response: Mapping[str, object]) -> dict[str, object]:
    """Convert a market-research ``FullResponse`` dict into quota-estimator ``research_data``.

    The implied revenue growth rate is derived from the predicted base-case
    revenue versus the latest historical revenue. When either figure is
    missing the growth hint is omitted and the quota estimator falls back to
    its trend-only behavior.
    """
    if not isinstance(full_response, Mapping):
        raise ValueError("market-research payload must be an object.")

    company = str(full_response.get("company") or "the customer")
    ticker = full_response.get("ticker")
    sector = full_response.get("sector")
    prediction = full_response.get("prediction")

    latest_revenue = _latest_historical_revenue(full_response.get("historical"))
    base_revenue = _predicted_base_revenue(prediction)

    growth_rate: float | None = None
    if latest_revenue is not None and latest_revenue > 0 and base_revenue is not None:
        growth_rate = round((base_revenue - latest_revenue) / latest_revenue, 4)

    confidence = ""
    methodology = ""
    if isinstance(prediction, Mapping):
        confidence = str(prediction.get("confidence") or "")
        methodology = str(prediction.get("methodology_summary") or "")

    ticker_suffix = f" ({ticker})" if ticker else ""
    if growth_rate is not None:
        summary = (
            f"{company}{ticker_suffix} market-research forecast implies "
            f"{growth_rate * 100:.1f}% revenue growth next fiscal year"
        )
        if confidence:
            summary += f" ({confidence} confidence)"
        summary += "."
    else:
        summary = f"{company}{ticker_suffix} market-research forecast supplied without a derivable growth rate."
    if methodology:
        summary += f" {methodology}"

    research: dict[str, object] = {
        "company_name": company,
        "summary": summary,
        "articles": _build_articles(full_response, company),
    }
    if sector:
        research["sector"] = str(sector)
    if growth_rate is not None:
        research["growth_rate"] = growth_rate
        research["key_metrics"] = {"revenue_yoy_growth": growth_rate}
    return research


def _build_articles(full_response: Mapping[str, object], company: str) -> list[dict[str, str]]:
    """Turn market-research data-source attribution into citable articles."""
    articles: list[dict[str, str]] = []
    data_sources = full_response.get("data_sources")
    if isinstance(data_sources, Mapping):
        for label, source in data_sources.items():
            if not source:
                continue
            articles.append(
                {
                    "title": f"{company} {str(label).replace('_', ' ')} data",
                    "source": str(source),
                    "url": "",
                }
            )

    prediction = full_response.get("prediction")
    if isinstance(prediction, Mapping):
        consensus = prediction.get("analyst_consensus")
        if isinstance(consensus, Mapping) and consensus.get("source"):
            articles.append(
                {
                    "title": f"{company} analyst consensus",
                    "source": str(consensus.get("source")),
                    "url": "",
                }
            )

    if not articles:
        articles.append(
            {
                "title": f"{company} market-research forecast",
                "source": "market-research agent",
                "url": "",
            }
        )
    return articles
