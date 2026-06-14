"""Unit tests for the quota estimation pipeline and artifact renderers."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from src.agents.quota_estimator.pipeline import build_quota_estimate, generate_quota_estimation_report


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
        {
            "territory": "Southwest",
            "category": "Toys",
            "order_date": "2025-08-15",
            "revenue": 75000,
            "quantity": 180,
        },
        {
            "territory": "Southwest",
            "category": "Toys",
            "order_date": "2026-03-15",
            "revenue": 90000,
            "quantity": 210,
        },
    ]


def _research_data() -> dict[str, object]:
    return {
        "summary": "Novelty goods demand is expanding with 12% year-over-year retail growth.",
        "key_metrics": {"revenue_yoy_growth": "12%"},
        "articles": [
            {
                "title": "Retail novelty goods expand",
                "source": "Example Research",
                "url": "https://example.com/research",
            }
        ],
    }


def _workiq_activity(score: str = "High") -> dict[str, object]:
    return {
        "source": "mock WorkIQ",
        "engagement_score": score,
        "last_contact": "2026-05-28",
        "recent_activity": [
            {"type": "email", "subject": "FY27 planning"},
            {"type": "meeting", "subject": "Quota workshop"},
        ],
    }


def test_build_quota_estimate_groups_sales_and_includes_context() -> None:
    estimate = build_quota_estimate(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=_research_data(),
        workiq_activity=_workiq_activity(),
    )

    assert estimate.customer_name == "Tailspin Toys"
    assert len(estimate.recommendations) == 2
    assert estimate.trailing_revenue_total == 395000
    assert estimate.recommended_quota_total > estimate.trailing_revenue_total
    assert estimate.research_context.growth_rate_hint == pytest.approx(0.12)
    assert estimate.workiq_activity.activity_count == 2
    assert any("SalesOrderHeader" in citation for citation in estimate.citations)
    assert any("Retail novelty goods expand" in citation for citation in estimate.citations)


def test_workiq_engagement_adjusts_recommended_quota() -> None:
    high = build_quota_estimate(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=_research_data(),
        workiq_activity=_workiq_activity("High"),
    )
    low = build_quota_estimate(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=_research_data(),
        workiq_activity=_workiq_activity("Low"),
    )

    assert high.recommended_quota_total > low.recommended_quota_total


def test_generate_quota_estimation_report_creates_artifacts(tmp_path: Path) -> None:
    result = generate_quota_estimation_report(
        customer_name="Tailspin Toys",
        sales_rows=_sales_rows(),
        research_data=_research_data(),
        workiq_activity=_workiq_activity(),
        output_dir=tmp_path,
    )

    artifacts = result["artifacts"]
    assert isinstance(artifacts, dict)
    assert set(artifacts) == {"xlsx", "html", "pdf"}

    workbook = openpyxl.load_workbook(artifacts["xlsx"])
    assert workbook.sheetnames == ["Summary", "Recommendations", "Sales Detail", "Methodology"]

    html_path = Path(str(artifacts["html"]))
    assert "<html" in html_path.read_text(encoding="utf-8").lower()

    pdf_path = Path(str(artifacts["pdf"]))
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_generate_quota_estimation_report_rejects_unsupported_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported quota report format"):
        generate_quota_estimation_report(
            customer_name="Tailspin Toys",
            sales_rows=_sales_rows(),
            output_dir=tmp_path,
            formats=["xlsx", "docx"],
        )


def test_build_quota_estimate_requires_sales_rows() -> None:
    with pytest.raises(ValueError, match="sales_rows must include"):
        build_quota_estimate(customer_name="Tailspin Toys", sales_rows=[])
