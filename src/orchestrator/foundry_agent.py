"""Azure AI Foundry sales orchestrator combining Fabric IQ, WorkIQ, and local tools.

This module defines the WWI prompt-agent used by the demo. The agent runs in Azure AI
Foundry, queries structured sales data through Fabric IQ, optionally enriches account context
with WorkIQ, and can invoke local Python tools for quota forecasting and DOCX report generation.
Local tools use strict JSON schemas so the model can call them reliably without exposing Python
stack traces back to the conversation.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    FabricIQPreviewTool,
    FunctionTool,
    MCPTool,
    PromptAgentDefinition,
    Tool,
    WorkIQPreviewTool,
)
from azure.identity import DefaultAzureCredential

from src.orchestrator.config import OrchestratorConfig

if TYPE_CHECKING:
    from src.agents.report_generator.generator import ForecastData, ForecastItem

logger = logging.getLogger(__name__)

_AGENT_NAME = "WWISalesAgent"
_DEFAULT_REPORT_TEMPLATE = "account_plan.md"
_MAX_FUNCTION_CALL_ROUNDS = 8

_AGENT_INSTRUCTIONS = """You are a sales analyst for Wide World Importers (WWI), a wholesale novelty goods company.

Your capabilities:
1. SALES DATA: Query the WWI data warehouse via Fabric IQ for sales transactions,
   customers, products, geography, and employees. Write correct T-SQL for Fabric.
2. ACTIVITY DATA: When WorkIQ is available, retrieve M365 activity signals
   (emails, meetings, engagement) for customer context.
3. QUOTA FORECAST: Generate FY quota projections based on trailing 12-month sales trends.
4. REPORTS: Generate formatted DOCX reports with charts and citations.

Guidelines:
- Use markdown tables for multi-row results
- Round currency to 2 decimal places
- Include totals/averages where appropriate
- Cite data sources
- Proactively surface insights the user might not have asked for
- When comparing time periods, show both absolute values and percentage change"""

ACCOUNT_ACTIVITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        }
    },
    "required": ["customer_name"],
    "additionalProperties": False,
}

FORECAST_QUOTA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        }
    },
    "required": ["customer_name"],
    "additionalProperties": False,
}

_FORECAST_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "description": "Forecast category name."},
        "current_fy_revenue": {"type": "number", "description": "Current fiscal year revenue."},
        "growth_rate": {"type": "number", "description": "Projected growth rate as a decimal."},
        "projected_fy_revenue": {"type": "number", "description": "Projected fiscal year revenue."},
    },
    "required": ["category", "current_fy_revenue", "growth_rate", "projected_fy_revenue"],
    "additionalProperties": False,
}

_FORECAST_DATA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Optional quota forecast payload to render in the DOCX report.",
    "properties": {
        "current_fy_total": {"type": "number", "description": "Current fiscal year total revenue."},
        "projected_fy_total": {"type": "number", "description": "Projected fiscal year total revenue."},
        "overall_growth_rate": {"type": "number", "description": "Overall projected growth rate."},
        "methodology": {"type": "string", "description": "Short description of the forecast methodology."},
        "items": {
            "type": "array",
            "description": "Forecast line items by category.",
            "items": _FORECAST_ITEM_SCHEMA,
        },
    },
    "required": ["current_fy_total", "projected_fy_total", "overall_growth_rate", "methodology", "items"],
    "additionalProperties": False,
}

_REPORT_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "deal_name": {"type": "string", "description": "Opportunity or deal name."},
        "value": {"type": "number", "description": "Opportunity value in customer currency."},
        "stage": {"type": "string", "description": "Current sales stage."},
        "close_date": {"type": "string", "description": "Expected close date."},
    },
    "required": ["deal_name", "value", "stage", "close_date"],
    "additionalProperties": False,
}

GENERATE_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Title for the generated report."},
        "customer_name": {
            "type": "string",
            "description": "Customer or prospect account name.",
        },
        "sections": {
            "type": "array",
            "description": "Deprecated alias for pipeline_data.",
            "items": _REPORT_SECTION_SCHEMA,
        },
        "pipeline_data": {
            "type": "array",
            "description": "Pipeline rows to include in the report.",
            "items": _REPORT_SECTION_SCHEMA,
        },
        "research_data": {
            "type": "object",
            "description": "Customer research payload with summary and article metadata.",
            "additionalProperties": True,
        },
        "sharepoint_docs": {
            "type": "array",
            "description": "Referenced SharePoint documents with name, url, and excerpt.",
            "items": {"type": "object", "additionalProperties": True},
        },
        "forecast_data": {
            "anyOf": [
                _FORECAST_DATA_SCHEMA,
                {"type": "null"},
            ],
            "description": "Optional quota forecast payload to render in the DOCX report.",
        },
        "additional_context": {
            "type": "string",
            "description": "Additional notes to append to the report.",
        },
    },
    "required": ["title", "customer_name"],
    "additionalProperties": False,
}

ToolDefinition = FabricIQPreviewTool | WorkIQPreviewTool | FunctionTool | MCPTool
ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]
PromptAgent = Any  # Azure AI Projects prompt-agent models are SDK-generated and do not ship precise stubs.
ResponsePayload = Any  # Responses API payloads are dynamic SDK objects without complete public typings.


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
    """Return a demo fiscal-year quota forecast with structured category data."""
    customer = arguments.get("customer_name", "Unknown")
    items = [
        {
            "category": "Novelty Items",
            "current_fy_revenue": 450000,
            "growth_rate": 0.12,
            "projected_fy_revenue": 504000,
        },
        {
            "category": "Clothing",
            "current_fy_revenue": 320000,
            "growth_rate": 0.12,
            "projected_fy_revenue": 358400,
        },
        {
            "category": "Computing Novelties",
            "current_fy_revenue": 280000,
            "growth_rate": 0.10,
            "projected_fy_revenue": 308000,
        },
        {
            "category": "Toys",
            "current_fy_revenue": 200000,
            "growth_rate": 0.15,
            "projected_fy_revenue": 230000,
        },
    ]
    return {
        "customer": customer,
        "current_fy_total": sum(item["current_fy_revenue"] for item in items),
        "projected_fy_total": sum(item["projected_fy_revenue"] for item in items),
        "overall_growth_rate": 0.12,
        "methodology": "Trailing 12-month sales trend with category-specific growth rates (demo data)",
        "items": items,
    }


def _parse_forecast_data(raw: object, customer_name: str) -> ForecastData | None:
    """Parse LLM-produced forecast payload into ForecastData, tolerating imperfect JSON."""
    from src.agents.report_generator.generator import ForecastData, ForecastItem

    if not isinstance(raw, dict):
        return None

    raw_items = raw.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    items: list[ForecastItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        try:
            items.append(
                ForecastItem(
                    category=str(entry.get("category", "Unknown")),
                    current_fy_revenue=float(str(entry.get("current_fy_revenue", 0))),
                    growth_rate=float(str(entry.get("growth_rate", 0))),
                    projected_fy_revenue=float(str(entry.get("projected_fy_revenue", 0))),
                )
            )
        except (TypeError, ValueError):
            continue

    if not items:
        return None

    def _safe_float(value: object) -> float:
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return 0.0

    return ForecastData(
        customer_name=customer_name,
        current_fy_total=_safe_float(raw.get("current_fy_total", 0)),
        projected_fy_total=_safe_float(raw.get("projected_fy_total", 0)),
        overall_growth_rate=_safe_float(raw.get("overall_growth_rate", 0)),
        methodology=str(raw.get("methodology", "Not specified")),
        items=items,
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
    }


def _slugify_filename(value: str) -> str:
    """Convert a report title into a filesystem-safe stem."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip().lower()).strip("._")
    return cleaned or "sales_report"


def _build_function_tool(name: str, description: str, parameters: dict[str, Any]) -> FunctionTool:
    """Create a strict function-tool definition for local Python handlers."""
    return FunctionTool(name=name, description=description, parameters=parameters, strict=True)


def _build_tools(config: OrchestratorConfig) -> tuple[list[ToolDefinition], dict[str, ToolHandler]]:
    """Build the tool list and local function handlers for the prompt agent."""
    tools: list[ToolDefinition] = [
        FabricIQPreviewTool(
            project_connection_id=config.fabric_iq_connection_id,
            require_approval="never",
        )
    ]
    handlers: dict[str, ToolHandler] = {
        "forecast_quota": forecast_quota_func,
        "generate_report": generate_report_func,
    }

    if config.workiq_connection_id:
        tools.append(WorkIQPreviewTool(project_connection_id=config.workiq_connection_id))
    else:
        tools.append(
            _build_function_tool(
                name="get_account_activity",
                description="Retrieve recent M365 activity signals for a customer account.",
                parameters=ACCOUNT_ACTIVITY_SCHEMA,
            )
        )
        handlers["get_account_activity"] = mock_workiq_func

    tools.extend(
        [
            _build_function_tool(
                name="forecast_quota",
                description="Generate an FY quota projection for a named customer account.",
                parameters=FORECAST_QUOTA_SCHEMA,
            ),
            _build_function_tool(
                name="generate_report",
                description="Generate a formatted DOCX sales report for a customer account.",
                parameters=GENERATE_REPORT_SCHEMA,
            ),
        ]
    )

    return tools, handlers


def _get_or_create_agent(project_client: AIProjectClient, config: OrchestratorConfig) -> PromptAgent:
    """Create a fresh agent version so config and tool changes are always applied."""
    logger.info(
        "Creating fresh version of agent %s; clean up unused historical versions in Azure AI Foundry as needed.",
        _AGENT_NAME,
    )
    tools, handlers = _build_tools(config)
    agent = project_client.agents.create_version(
        agent_name=_AGENT_NAME,
        definition=PromptAgentDefinition(
            model=config.model_deployment_name,
            instructions=_AGENT_INSTRUCTIONS,
            tools=cast(list[Tool], tools),
        ),
    )
    setattr(agent, "_local_function_handlers", handlers)
    return agent


def _item_value(item: Any, field: str, default: Any = None) -> Any:
    """Read a field from either a pydantic model or a plain dict."""
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def _execute_local_functions(agent: PromptAgent, response: ResponsePayload) -> list[dict[str, str]]:
    """Execute local function calls requested by the Foundry response payload."""
    handlers: dict[str, ToolHandler] = getattr(agent, "_local_function_handlers", {})
    tool_outputs: list[dict[str, str]] = []

    for item in getattr(response, "output", []) or []:
        if _item_value(item, "type") != "function_call":
            continue

        name = _item_value(item, "name", "")
        raw_arguments = _item_value(item, "arguments", "{}")
        call_id = _item_value(item, "call_id") or _item_value(item, "id")
        handler = handlers.get(name)

        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError:
            arguments = {}

        if handler is None:
            result = {"error": f"Unknown function: {name}"}
        else:
            try:
                result = handler(arguments if isinstance(arguments, dict) else {})
            except Exception as exc:  # noqa: BLE001 - local tool failures must not bubble into the model runtime.
                logger.exception("Local function %s failed", name)
                result = {
                    "error": "tool_execution_failed",
                    "function": name,
                    "message": str(exc),
                }

        if call_id:
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": str(call_id),
                    "output": json.dumps(result, default=str),
                }
            )

    return tool_outputs


def _extract_output_text(response: ResponsePayload) -> str:
    """Return the text content from a responses API payload."""
    output_text = getattr(response, "output_text", "")
    if isinstance(output_text, str) and output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        if _item_value(item, "type") != "message":
            continue
        for content in _item_value(item, "content", []) or []:
            text = _item_value(content, "text")
            if isinstance(text, str):
                chunks.append(text)
                continue
            text_value = _item_value(text, "value")
            if isinstance(text_value, str):
                chunks.append(text_value)

    return "\n".join(chunk for chunk in chunks if chunk) or "(no response text returned)"


def run_query(question: str, config: OrchestratorConfig | None = None) -> str:
    """Run a user question through the Foundry sales agent and return the final response text."""
    if config is None:
        config = OrchestratorConfig.from_env()

    with DefaultAzureCredential() as credential:
        with AIProjectClient(
            endpoint=config.foundry_project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project_client:
            openai_client = project_client.get_openai_client()
            agent = _get_or_create_agent(project_client, config)
            extra_body = {"agent_reference": {"name": agent.name, "type": "agent_reference"}}

            response = openai_client.responses.create(
                input=question,
                extra_body=extra_body,
            )

            tool_outputs: list[dict[str, str]] = []
            round_num = 0
            for round_num in range(1, _MAX_FUNCTION_CALL_ROUNDS + 1):
                tool_outputs = _execute_local_functions(agent, response)
                if not tool_outputs:
                    break

                response = openai_client.responses.create(
                    input=cast(Any, tool_outputs),
                    previous_response_id=response.id,
                    extra_body=extra_body,
                )

            if round_num >= _MAX_FUNCTION_CALL_ROUNDS and tool_outputs:
                logger.warning("Agent exceeded %d tool-calling rounds", _MAX_FUNCTION_CALL_ROUNDS)
                return (
                    "The agent exceeded the maximum number of tool-calling rounds. "
                    "Please simplify your request or try again."
                )

            return _extract_output_text(response)
