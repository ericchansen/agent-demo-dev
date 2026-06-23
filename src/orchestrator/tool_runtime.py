"""Dependency-light local tool runtime shared by Foundry prompt and hosted agents."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.quota_estimator.pipeline import (
    build_quota_estimate,
    demo_research_data,
    demo_sales_rows,
    demo_workiq_activity,
    forecast_payload_from_estimate,
    generate_quota_estimation_report,
)
from src.orchestrator.databricks_genie import databricks_genie_query_func
from src.orchestrator.tool_schemas import (
    ACCOUNT_ACTIVITY_SCHEMA,
    COMPUTE_ATTAINMENT_SCHEMA,
    DATABRICKS_QUERY_SCHEMA,
    FABRIC_QUERY_SCHEMA,
    FORECAST_QUOTA_SCHEMA,
    GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA,
    GENERATE_REPORT_SCHEMA,
    WEB_RESEARCH_SCHEMA,
)

__all__ = [
    "ACCOUNT_ACTIVITY_SCHEMA",
    "COMPUTE_ATTAINMENT_SCHEMA",
    "DATABRICKS_QUERY_SCHEMA",
    "FABRIC_QUERY_SCHEMA",
    "FORECAST_QUOTA_SCHEMA",
    "GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA",
    "GENERATE_REPORT_SCHEMA",
    "WEB_RESEARCH_SCHEMA",
    "compute_attainment_func",
    "databricks_genie_query_func",
    "demo_fabric_query_func",
    "forecast_quota_func",
    "generate_quota_estimation_report_func",
    "generate_report_func",
    "mock_workiq_func",
    "web_research_func",
]

_DEFAULT_REPORT_TEMPLATE = "account_plan.md"

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def demo_fabric_query_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return demo-safe sales rows for environments without a live Fabric connection.

    The Foundry ``FabricIQPreviewTool`` and the hosted ``fabric_query`` MCP path both
    require a provisioned Fabric Data Agent. This fallback lets the agent answer sales-data
    questions (and feed the quota estimator) on day one of the workshop, before attendees
    have wired Fabric IQ or Databricks Genie. Rows match the schema the quota tools expect:
    territory, category, order_date, revenue, quantity.
    """
    question = str(arguments.get("question", "")).strip()
    rows = demo_sales_rows()
    return {
        "status": "ok",
        "source": "demo (no live Fabric connection configured)",
        "question": question,
        "rows": rows,
        "row_count": len(rows),
        "note": (
            "Synthetic sales rows. Configure FABRIC_IQ_CONNECTION_ID "
            "(Fabric Data Agent) or a Databricks Genie connection to query real data."
        ),
    }


def mock_workiq_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return mock M365 activity data when WorkIQ is not available."""
    customer = arguments.get("customer_name", "Unknown")
    return {
        "customer": customer,
        "source": "mock (WorkIQ not available on this tenant)",
        "recent_activity": [
            {
                "type": "email",
                "subject": f"Re: FY27 Planning - {customer}",
                "date": "2026-05-28",
                "participants": ["AE", "Champion"],
            },
            {
                "type": "meeting",
                "subject": f"QBR Prep - {customer}",
                "date": "2026-05-15",
                "duration_min": 60,
            },
            {
                "type": "email",
                "subject": f"Updated pricing proposal - {customer}",
                "date": "2026-05-10",
                "participants": ["AE", "Procurement"],
            },
            {
                "type": "meeting",
                "subject": f"Technical deep dive - {customer}",
                "date": "2026-04-22",
                "duration_min": 90,
            },
        ],
        "engagement_score": "High",
        "last_contact": "2026-05-28",
    }


def forecast_quota_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return a legacy FY quota forecast payload using the shared estimator."""
    customer = arguments.get("customer_name", "Unknown")
    customer_name = str(customer)
    scenario = arguments.get("scenario")
    estimate = build_quota_estimate(
        customer_name=customer_name,
        sales_rows=demo_sales_rows(),
        research_data=demo_research_data(customer_name),
        workiq_activity=demo_workiq_activity(customer_name),
        scenario=str(scenario) if scenario is not None else "base",
    )
    return forecast_payload_from_estimate(estimate)


def generate_quota_estimation_report_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate quota estimation XLSX, HTML, and PDF artifacts from normalized sales rows."""
    customer_name = str(arguments.get("customer_name", "Unknown"))
    sales_rows = arguments.get("sales_rows")
    if not isinstance(sales_rows, list) or not all(isinstance(item, dict) for item in sales_rows):
        raise ValueError("sales_rows must be a list of objects from Fabric IQ or Databricks Genie.")

    research_data = arguments.get("research_data")
    if research_data is not None and not isinstance(research_data, dict):
        raise ValueError("research_data must be an object when provided.")

    workiq_activity = arguments.get("workiq_activity")
    if workiq_activity is not None and not isinstance(workiq_activity, dict):
        raise ValueError("workiq_activity must be an object when provided.")

    formats = arguments.get("formats")
    if formats is not None and not isinstance(formats, list):
        raise ValueError("formats must be a list of strings when provided.")

    scenario = arguments.get("scenario")
    if scenario is not None and not isinstance(scenario, str):
        raise ValueError("scenario must be a string when provided.")

    data_source = arguments.get("data_source")
    if data_source is not None and not isinstance(data_source, str):
        raise ValueError("data_source must be a string when provided.")

    return generate_quota_estimation_report(
        customer_name=customer_name,
        sales_rows=sales_rows,
        research_data=research_data,
        workiq_activity=workiq_activity,
        data_source=data_source,
        scenario=scenario if scenario is not None else "base",
        output_dir=str(arguments.get("output_dir", "output/quota-estimates")),
        formats=[str(item) for item in formats] if formats is not None else None,
    )


def generate_report_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate a DOCX sales report and return the resolved file metadata."""
    from src.agents.report_generator.generator import _build_report_data, generate_docx

    report_arguments = dict(arguments)
    if "pipeline_data" not in report_arguments and isinstance(report_arguments.get("sections"), list):
        report_arguments["pipeline_data"] = report_arguments["sections"]

    data = _build_report_data(report_arguments)
    generated_at = datetime.now()

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = _slugify_filename(data.title)
    output_path = output_dir / f"{safe_title}_{generated_at:%Y%m%d_%H%M%S}.docx"
    resolved_output_path = output_path.resolve()

    generate_docx(data, _DEFAULT_REPORT_TEMPLATE, resolved_output_path)

    return {
        "status": "generated",
        "file_path": str(resolved_output_path),
        "format": "docx",
        "title": data.title,
        "has_forecast": data.forecast_data is not None,
        "has_chart": data.forecast_data is not None,
        "note": (
            "File written locally. In a deployed M365 agent, upload to OneDrive/SharePoint and return a sharing link."
        ),
    }


def web_research_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Simulate web research for market intelligence."""
    query = arguments.get("query", "")
    customer = arguments.get("customer_name", "the customer")
    return {
        "query": query,
        "source": "demo (simulated web research)",
        "findings": [
            {
                "title": "Wholesale Novelty Market Trends 2026",
                "url": "https://example.com/market-trends-2026",
                "source": "Industry Weekly",
                "date": "2026-05-15",
                "snippet": (
                    "The wholesale novelty goods market is projected to grow 8.5% YoY "
                    "driven by seasonal demand and e-commerce expansion."
                ),
                "sales_implication": "Growth tailwind - budget for increased inventory and fulfillment capacity.",
            },
            {
                "title": f"{customer} Expands Distribution Network",
                "url": "https://example.com/expansion-news",
                "source": "Business Journal",
                "date": "2026-06-01",
                "snippet": (
                    f"{customer} announced plans to open 3 new regional "
                    "distribution centers, increasing their total to 15."
                ),
                "sales_implication": (
                    "Upsell opportunity - new DCs need initial inventory stocking across all categories."
                ),
            },
            {
                "title": "Supply Chain Costs Stabilizing in Q2 2026",
                "url": "https://example.com/supply-chain",
                "source": "Logistics Today",
                "date": "2026-04-20",
                "snippet": (
                    "Freight and raw material costs have declined 12% from 2025 peaks, improving wholesale margins."
                ),
                "sales_implication": (
                    "Margin improvement - customers may be receptive to volume commitments at current pricing."
                ),
            },
        ],
        "tailwinds": ["Market growing 8.5% YoY", "Customer expanding distribution", "Supply costs stabilizing"],
        "headwinds": ["Increased competition from direct-to-consumer brands", "Seasonal demand uncertainty"],
    }


def compute_attainment_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Compute quota attainment metrics from provided sales figures."""
    annual_target = arguments.get("annual_target", 0)
    ytd_actual = arguments.get("ytd_actual", 0)
    open_pipeline = arguments.get("open_pipeline", 0)
    months_elapsed = arguments.get("months_elapsed", 6)
    days_elapsed = arguments.get("days_elapsed", 180)

    pro_rata_target = annual_target * (months_elapsed / 12) if annual_target else 0
    attainment_pct = (ytd_actual / pro_rata_target * 100) if pro_rata_target else 0
    remaining_quota = max(annual_target - ytd_actual, 0)
    pipeline_coverage = (open_pipeline / remaining_quota) if remaining_quota else 0
    daily_rate = (ytd_actual / days_elapsed) if days_elapsed else 0
    run_rate_projection = daily_rate * 365

    if attainment_pct >= 90 and pipeline_coverage >= 2.0:
        risk_rating = "Green"
    elif attainment_pct >= 70 or pipeline_coverage >= 1.5:
        risk_rating = "Yellow"
    else:
        risk_rating = "Red"

    return {
        "annual_target": annual_target,
        "ytd_actual": ytd_actual,
        "attainment_pct": round(attainment_pct, 1),
        "pipeline_coverage": round(pipeline_coverage, 2),
        "run_rate_projection": round(run_rate_projection, 0),
        "risk_rating": risk_rating,
        "remaining_quota": round(remaining_quota, 0),
        "daily_rate": round(daily_rate, 0),
    }


def _slugify_filename(value: str) -> str:
    """Convert a report title into a filesystem-safe stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().lower()).strip("._")
    return cleaned or "sales_report"
