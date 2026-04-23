"""Unit tests for the Researcher Agent tools (mock provider)."""

from __future__ import annotations

import pytest

from src.agents.researcher.tools import research_company

# Ensure mock provider is active for all tests in this module.
pytestmark = pytest.mark.usefixtures("_mock_search_provider")


@pytest.fixture(autouse=True)
def _mock_search_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.agents.researcher.tools._SEARCH_PROVIDER", "mock")


# ---------------------------------------------------------------------------
# Structure validation
# ---------------------------------------------------------------------------


async def test_mock_returns_valid_structure() -> None:
    """Mock mode should return a dict with the expected top-level keys."""
    result = await research_company("Tailspin Toys")

    assert isinstance(result, dict)
    assert "company_name" in result
    assert "summary" in result
    assert "articles" in result
    assert "key_metrics" in result

    assert isinstance(result["summary"], str)
    assert isinstance(result["articles"], list)
    assert isinstance(result["key_metrics"], dict)


async def test_mock_articles_have_required_fields() -> None:
    """Each article dict should contain title, url, snippet, and date."""
    result = await research_company("Tailspin Toys")
    required_keys = {"title", "url", "snippet", "date"}

    for article in result["articles"]:
        assert required_keys.issubset(article.keys()), f"Missing keys in article: {article}"


# ---------------------------------------------------------------------------
# Company-name passthrough
# ---------------------------------------------------------------------------


async def test_company_name_in_response() -> None:
    """The response company_name should match the input."""
    result = await research_company("Contoso Ltd")
    assert result["company_name"] == "Contoso Ltd"


async def test_tailspin_returns_rich_data() -> None:
    """Tailspin Toys (the mock target) should return articles and metrics."""
    result = await research_company("Tailspin Toys")
    assert result["company_name"] == "Tailspin Toys"
    assert len(result["articles"]) > 0
    assert len(result["key_metrics"]) > 0


async def test_unknown_company_returns_empty_articles() -> None:
    """A company not in the mock data should return an empty articles list."""
    result = await research_company("Unknown Corp")
    assert result["company_name"] == "Unknown Corp"
    assert result["articles"] == []


# ---------------------------------------------------------------------------
# focus_areas parameter
# ---------------------------------------------------------------------------


async def test_focus_areas_accepted() -> None:
    """Passing focus_areas should not raise and the result structure is intact."""
    result = await research_company("Tailspin Toys", focus_areas="earnings")
    assert result["company_name"] == "Tailspin Toys"
    assert "summary" in result


async def test_focus_areas_none_default() -> None:
    """Omitting focus_areas should default to None and work fine."""
    result = await research_company("Tailspin Toys")
    assert isinstance(result, dict)
