"""Research tools — web search for company intelligence."""

from __future__ import annotations

import os
from typing import Any

import aiohttp

_SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "mock")
_SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_TAILSPIN_MOCK: dict[str, Any] = {
    "company_name": "Tailspin Toys",
    "summary": (
        "Tailspin Toys is a mid-market novelty goods manufacturer expanding into "
        "digital-first retail channels. Recent earnings show 12% YoY revenue growth "
        "driven by new licensing partnerships and direct-to-consumer e-commerce."
    ),
    "articles": [
        {
            "title": "Tailspin Toys Reports Strong Q3 Results",
            "url": "https://example.com/tailspin-q3",
            "snippet": "Revenue rose 12% year-over-year to $340 M, beating analyst estimates.",
            "date": "2025-07-15",
        },
        {
            "title": "Tailspin Toys Announces APAC Expansion",
            "url": "https://example.com/tailspin-apac",
            "snippet": "The company will open distribution centres in Singapore and Tokyo by Q1 2026.",
            "date": "2025-06-20",
        },
        {
            "title": "Tailspin Toys Launches D2C Platform",
            "url": "https://example.com/tailspin-d2c",
            "snippet": "A new direct-to-consumer storefront aims to boost margins by 5 pp.",
            "date": "2025-05-10",
        },
    ],
    "key_metrics": {
        "revenue_yoy_growth": "12%",
        "market_cap": "$2.1B",
        "employee_count": 4500,
    },
}

_GENERIC_MOCK: dict[str, Any] = {
    "company_name": "",  # filled at runtime
    "summary": "No detailed research available in mock mode for this company.",
    "articles": [],
    "key_metrics": {},
}


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------


async def _search_bing(query: str) -> list[dict[str, Any]]:
    """Call Bing Web Search API v7 and return normalized article dicts."""
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": _SEARCH_API_KEY}
    params = {"q": query, "count": "5", "mkt": "en-US"}

    async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
        async with session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()

    articles: list[dict[str, Any]] = []
    for page in data.get("webPages", {}).get("value", []):
        articles.append(
            {
                "title": page.get("name", ""),
                "url": page.get("url", ""),
                "snippet": page.get("snippet", ""),
                "date": page.get("dateLastCrawled", "")[:10],
            }
        )
    return articles


async def _search_tavily(query: str) -> list[dict[str, Any]]:
    """Call Tavily Search API and return normalized article dicts."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": _SEARCH_API_KEY,
        "query": query,
        "max_results": 5,
        "include_answer": False,
    }

    async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()

    articles: list[dict[str, Any]] = []
    for result in data.get("results", []):
        articles.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("content", "")[:300],
                "date": result.get("published_date", ""),
            }
        )
    return articles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def research_company(
    company_name: str,
    focus_areas: str | None = None,
) -> dict[str, Any]:
    """Research a company via web search and return structured intelligence.

    Parameters
    ----------
    company_name:
        The company to research.
    focus_areas:
        Optional comma-separated focus areas (news, earnings, strategy, expansion).
        When provided, the search query is refined to include these topics.

    Returns
    -------
    dict with keys: company_name, summary, articles, key_metrics
    """
    provider = _SEARCH_PROVIDER.lower()

    # -- Mock provider -------------------------------------------------------
    if provider == "mock":
        if company_name.lower().strip() == "tailspin toys":
            return _TAILSPIN_MOCK
        result = {**_GENERIC_MOCK, "company_name": company_name}
        return result

    # -- Build search query --------------------------------------------------
    query = f"{company_name} company"
    if focus_areas:
        query += f" {focus_areas}"

    # -- Live providers ------------------------------------------------------
    try:
        if provider == "bing":
            articles = await _search_bing(query)
        elif provider == "tavily":
            articles = await _search_tavily(query)
        else:
            return {
                "company_name": company_name,
                "summary": f"Unknown search provider: {provider}",
                "articles": [],
                "key_metrics": {},
            }
    except aiohttp.ClientError as exc:
        return {
            "company_name": company_name,
            "summary": f"Search request failed: {exc}",
            "articles": [],
            "key_metrics": {},
        }
    except TimeoutError:
        return {
            "company_name": company_name,
            "summary": "Search request timed out.",
            "articles": [],
            "key_metrics": {},
        }

    summary = (
        f"Found {len(articles)} results for {company_name}." if articles else f"No results found for {company_name}."
    )

    return {
        "company_name": company_name,
        "summary": summary,
        "articles": articles,
        "key_metrics": {},
    }
