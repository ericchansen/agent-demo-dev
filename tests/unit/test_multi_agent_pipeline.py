"""Unit tests for the working multi-agent pipeline proof of concept."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.quota_estimator.pipeline import (
    demo_research_data,
    demo_sales_rows,
    demo_workiq_activity,
    generate_quota_estimation_report,
)
from src.orchestrator.multi_agent import MultiAgentPipeline, run_multi_agent_pipeline


def test_multi_agent_pipeline_generates_quota_artifacts(tmp_path: Path) -> None:
    result = run_multi_agent_pipeline(
        "Generate a quota report for Tailspin Toys",
        customer_name="Tailspin Toys",
        output_dir=tmp_path,
    )

    quota_report = result["quota_report"]
    assert isinstance(quota_report, dict)
    assert set(quota_report["artifacts"]) == {"xlsx", "html", "pdf"}
    assert all(Path(str(path)).exists() for path in quota_report["artifacts"].values())
    assert "multi-agent pipeline" in str(result["response"])


def test_multi_agent_pipeline_supports_databricks_rows(tmp_path: Path) -> None:
    result = run_multi_agent_pipeline(
        "Generate an aggressive quota report for Tailspin Toys",
        customer_name="Tailspin Toys",
        data_source="databricks",
        scenario="aggressive",
        output_dir=tmp_path,
    )

    quota_report = result["quota_report"]
    assert isinstance(quota_report, dict)
    assert result["data_source"] == "databricks"
    assert all(
        {"territory", "category", "order_date", "revenue", "quantity", "source_platform"}.issubset(row)
        for row in result["sales_rows"]
    )
    assert {row["source_platform"] for row in result["sales_rows"]} == {"databricks"}
    assert "Databricks Genie" in str(quota_report["methodology"])


def test_multi_agent_pipeline_preserves_single_agent_summary(tmp_path: Path) -> None:
    rows = demo_sales_rows()
    research = demo_research_data("Tailspin Toys")
    workiq = demo_workiq_activity("Tailspin Toys")

    def data_agent(_customer_name: str, _data_source: str) -> list[dict[str, object]]:
        return rows

    def research_agent(_customer_name: str, _user_message: str) -> dict[str, object]:
        return research

    def work_agent(_customer_name: str) -> dict[str, object]:
        return workiq

    pipeline = MultiAgentPipeline(data_agent=data_agent, research_agent=research_agent, work_context_agent=work_agent)
    multi = pipeline.run(
        user_message="Generate a quota report for Tailspin Toys",
        customer_name="Tailspin Toys",
        output_dir=tmp_path / "multi",
    )
    single = generate_quota_estimation_report(
        customer_name="Tailspin Toys",
        sales_rows=rows,
        research_data=research,
        workiq_activity=workiq,
        output_dir=tmp_path / "single",
    )

    assert isinstance(multi.quota_report, dict)
    assert multi.quota_report["summary"] == single["summary"]


def test_multi_agent_pipeline_skips_report_when_not_requested(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def report_agent(arguments: dict[str, Any]) -> dict[str, object]:
        calls.append(arguments)
        return {}

    pipeline = MultiAgentPipeline(report_agent=report_agent)
    result = pipeline.run(
        user_message="Summarize Tailspin Toys sales context",
        customer_name="Tailspin Toys",
        output_dir=tmp_path,
    )

    assert result.quota_report is None
    assert calls == []
    assert "Ask for a report" in result.response


def test_multi_agent_agent_sequence_is_portal_ready() -> None:
    names = [agent.foundry_agent_name for agent in MultiAgentPipeline.agent_sequence]

    assert names == ["fsa-planner", "fsa-data", "fsa-research", "fsa-work-context", "fsa-conversation", "fsa-report"]
