from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture()
def sample_pipeline_data() -> list[dict]:
    """Sample CRM pipeline rows for testing."""
    return [
        {
            "customer": "Contoso Ltd",
            "deal_name": "Enterprise Platform",
            "value": 450_000,
            "stage": "Proposal",
            "close_date": "2025-09-30",
        },
        {
            "customer": "Northwind Traders",
            "deal_name": "Data Migration",
            "value": 120_000,
            "stage": "Negotiation",
            "close_date": "2025-08-15",
        },
        {
            "customer": "Adventure Works",
            "deal_name": "Cloud Adoption",
            "value": 275_000,
            "stage": "Discovery",
            "close_date": "2025-12-01",
        },
    ]


@pytest.fixture()
def sample_research_data() -> dict:
    """Sample company research payload for testing."""
    return {
        "company_name": "Contoso Ltd",
        "articles": [
            {
                "title": "Contoso Reports Record Q2 Earnings",
                "source": "Reuters",
                "date": "2025-07-10",
                "summary": "Contoso Ltd posted a 15% YoY revenue increase driven by cloud services.",
            },
            {
                "title": "Contoso Expands APAC Operations",
                "source": "Bloomberg",
                "date": "2025-06-22",
                "summary": "The company announced new offices in Singapore and Tokyo.",
            },
        ],
    }
