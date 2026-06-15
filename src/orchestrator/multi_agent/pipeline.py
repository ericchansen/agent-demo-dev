"""Deterministic multi-agent pipeline that mirrors the single-agent quota flow."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.agents.quota_estimator.pipeline import demo_sales_rows
from src.orchestrator.tool_runtime import (
    generate_quota_estimation_report_func,
    mock_workiq_func,
    web_research_func,
)


@dataclass(frozen=True)
class AgentRegistration:
    """Portal-visible Foundry agent identity for one stage of the pipeline."""

    name: str
    role: str
    foundry_agent_name: str


@dataclass(frozen=True)
class MultiAgentPipelineResult:
    """Structured output returned by the conversational multi-agent pipeline."""

    customer_name: str
    scenario: str
    data_source: str
    response: str
    sales_rows: list[Mapping[str, object]]
    research_data: Mapping[str, object]
    workiq_activity: Mapping[str, object]
    quota_report: Mapping[str, object] | None
    agent_sequence: list[AgentRegistration]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation for CLI and tests."""

        return {
            "customer_name": self.customer_name,
            "scenario": self.scenario,
            "data_source": self.data_source,
            "response": self.response,
            "sales_rows": [dict(row) for row in self.sales_rows],
            "research_data": dict(self.research_data),
            "workiq_activity": dict(self.workiq_activity),
            "quota_report": dict(self.quota_report) if self.quota_report is not None else None,
            "agent_sequence": [
                {
                    "name": agent.name,
                    "role": agent.role,
                    "foundry_agent_name": agent.foundry_agent_name,
                }
                for agent in self.agent_sequence
            ],
        }


DataAgentFn = Callable[[str, str], list[Mapping[str, object]]]
ResearchAgentFn = Callable[[str, str], Mapping[str, object]]
WorkContextAgentFn = Callable[[str], Mapping[str, object]]
ReportAgentFn = Callable[[dict[str, Any]], Mapping[str, object]]


class MultiAgentPipeline:
    """Coordinate specialized agents while preserving single-agent output parity."""

    agent_sequence = [
        AgentRegistration("planner", "Select the data, research, work-context, and reporting steps.", "fsa-planner"),
        AgentRegistration("data", "Query Fabric Data Agent or Databricks Genie for sales rows.", "fsa-data"),
        AgentRegistration("research", "Gather market and competitive intelligence.", "fsa-research"),
        AgentRegistration(
            "work-context", "Add M365 activity context from WorkIQ or demo fallback.", "fsa-work-context"
        ),
        AgentRegistration(
            "conversational", "Synthesize outputs and decide whether a report is needed.", "fsa-conversation"
        ),
        AgentRegistration("report", "Generate quota XLSX, HTML, and PDF artifacts.", "fsa-report"),
    ]

    def __init__(
        self,
        *,
        data_agent: DataAgentFn | None = None,
        research_agent: ResearchAgentFn | None = None,
        work_context_agent: WorkContextAgentFn | None = None,
        report_agent: ReportAgentFn | None = None,
    ) -> None:
        self._data_agent = data_agent or _demo_data_agent
        self._research_agent = research_agent or _demo_research_agent
        self._work_context_agent = work_context_agent or _demo_work_context_agent
        self._report_agent = report_agent or generate_quota_estimation_report_func

    def run(
        self,
        *,
        user_message: str,
        customer_name: str,
        data_source: str = "fabric",
        scenario: str = "base",
        output_dir: str | Path = Path("output") / "multi-agent",
        formats: Sequence[str] = ("xlsx", "html", "pdf"),
    ) -> MultiAgentPipelineResult:
        """Run the full planner -> data -> research -> context -> report chain."""

        sales_rows = self._data_agent(customer_name, data_source)
        research_data = self._research_agent(customer_name, user_message)
        workiq_activity = self._work_context_agent(customer_name)
        wants_report = _message_requests_report(user_message)
        quota_report: Mapping[str, object] | None = None

        if wants_report:
            quota_report = self._report_agent(
                {
                    "customer_name": customer_name,
                    "sales_rows": list(sales_rows),
                    "research_data": dict(research_data),
                    "workiq_activity": dict(workiq_activity),
                    "data_source": data_source,
                    "scenario": scenario,
                    "output_dir": str(output_dir),
                    "formats": list(formats),
                }
            )

        response = _build_conversational_response(
            customer_name=customer_name,
            data_source=data_source,
            scenario=scenario,
            quota_report=quota_report,
            wants_report=wants_report,
        )
        return MultiAgentPipelineResult(
            customer_name=customer_name,
            scenario=scenario,
            data_source=data_source,
            response=response,
            sales_rows=list(sales_rows),
            research_data=research_data,
            workiq_activity=workiq_activity,
            quota_report=quota_report,
            agent_sequence=self.agent_sequence,
        )


def run_multi_agent_pipeline(
    user_message: str,
    *,
    customer_name: str = "Wide World Importers",
    data_source: str = "fabric",
    scenario: str = "base",
    output_dir: str | Path = Path("output") / "multi-agent",
) -> dict[str, object]:
    """Invoke the working multi-agent pipeline as a single command-friendly function."""

    return (
        MultiAgentPipeline()
        .run(
            user_message=user_message,
            customer_name=customer_name,
            data_source=data_source,
            scenario=scenario,
            output_dir=output_dir,
        )
        .to_dict()
    )


def _demo_data_agent(customer_name: str, data_source: str) -> list[Mapping[str, object]]:
    rows = demo_sales_rows()
    if data_source.strip().lower() == "databricks":
        return [
            {
                "sales_territory": row["territory"],
                "productCategory": row["category"],
                "orderDate": row["order_date"],
                "net_sales_amount": row["revenue"],
                "units_sold": row["quantity"],
                "source_platform": "databricks",
                "customer_name": customer_name,
            }
            for row in rows
        ]
    return [dict(row, customer_name=customer_name, source_platform="fabric") for row in rows]


def _demo_research_agent(customer_name: str, user_message: str) -> Mapping[str, object]:
    research = web_research_func({"query": user_message, "customer_name": customer_name})
    findings = research.get("findings", [])
    articles = [
        {"title": item.get("title"), "source": item.get("source"), "url": item.get("url")}
        for item in findings
        if isinstance(item, Mapping)
    ]
    return {
        "company_name": customer_name,
        "summary": " ".join(str(item) for item in research.get("tailwinds", [])) or "No market tailwinds found.",
        "key_metrics": {"market_growth": "8.5%"},
        "articles": articles,
    }


def _demo_work_context_agent(customer_name: str) -> Mapping[str, object]:
    return mock_workiq_func({"customer_name": customer_name})


def _message_requests_report(user_message: str) -> bool:
    message = user_message.lower()
    return "report" in message or "artifact" in message or "xlsx" in message or "pdf" in message


def _build_conversational_response(
    *,
    customer_name: str,
    data_source: str,
    scenario: str,
    quota_report: Mapping[str, object] | None,
    wants_report: bool,
) -> str:
    if not wants_report:
        return (
            f"The conversational agent gathered {data_source} sales rows, market research, and WorkIQ context "
            f"for {customer_name}. Ask for a report to delegate artifact generation to the report agent."
        )

    summary = quota_report.get("summary", {}) if quota_report is not None else {}
    artifacts = quota_report.get("artifacts", {}) if quota_report is not None else {}
    return (
        f"Generated a {scenario} quota estimation report for {customer_name} using the multi-agent pipeline. "
        f"Summary: {json.dumps(summary, sort_keys=True)}. Artifacts: {json.dumps(artifacts, sort_keys=True)}"
    )
