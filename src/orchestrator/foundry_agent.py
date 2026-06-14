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
from typing import Any, cast

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

logger = logging.getLogger(__name__)

_AGENT_NAME = "WWISalesAgent"
_DEFAULT_REPORT_TEMPLATE = "account_plan.md"
_MAX_FUNCTION_CALL_ROUNDS = 15

_AGENT_INSTRUCTIONS = """You are a sales analyst for Wide World Importers (WWI), a wholesale novelty goods company.

Your capabilities:
1. SALES DATA: Query the WWI data warehouse via Fabric IQ for sales transactions,
   customers, products, geography, and employees. Write correct T-SQL for Fabric.
2. ACTIVITY DATA: When WorkIQ is available, retrieve M365 activity signals
   (emails, meetings, engagement) for customer context.
3. QUOTA FORECAST: Generate FY quota projections based on trailing 12-month sales trends.
4. REPORTS: Generate formatted DOCX reports with charts and citations.

New capabilities:
5. WEB RESEARCH: Search the web for market trends, customer news, and competitive
   intelligence to enrich sales analysis with external context.
6. QUOTA ATTAINMENT: Compute quota attainment metrics from sales data — pipeline
   coverage, run rate projection, and risk rating.

Guidelines:
- Use markdown tables for multi-row results
- Round currency to 2 decimal places
- Include totals/averages where appropriate
- Cite data sources with URLs when available
- Proactively surface insights the user might not have asked for
- When comparing time periods, show both absolute values and percentage change
- For deep analyses, gather data from multiple sources before synthesizing"""

_MARKET_DATA_INSTRUCTIONS = """

5. MARKET DATA: Query SEC EDGAR financial data for real US public companies via the
   real_world_market_data tool. Available metrics: revenue, net_income, total_assets
   from 10-K (annual) and 10-Q (quarterly) filings. Use this for competitive intelligence,
   industry analysis, and benchmarking against real-world companies.
   - Join company_financials to companies on cik for industry context
   - Cite SEC filing type and date in responses
   - Round large currency values to millions (e.g., $45,123M)"""


def _build_agent_instructions(config: OrchestratorConfig) -> str:
    """Generate agent instructions based on which connections are configured."""
    instructions = _AGENT_INSTRUCTIONS
    if config.market_data_connection_id:
        instructions += _MARKET_DATA_INSTRUCTIONS
    return instructions


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

WEB_RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query for market research, customer news, or competitive intelligence.",
        },
        "customer_name": {
            "type": "string",
            "description": "Optional customer name to contextualize results.",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}

COMPUTE_ATTAINMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "annual_target": {
            "type": "number",
            "description": "Annual quota target in dollars.",
        },
        "ytd_actual": {
            "type": "number",
            "description": "Year-to-date actual revenue in dollars.",
        },
        "open_pipeline": {
            "type": "number",
            "description": "Total value of open pipeline deals.",
        },
        "months_elapsed": {
            "type": "number",
            "description": "Number of months elapsed in current fiscal year.",
        },
        "days_elapsed": {
            "type": "number",
            "description": "Number of days elapsed in current fiscal year.",
        },
    },
    "required": ["annual_target", "ytd_actual", "open_pipeline", "months_elapsed", "days_elapsed"],
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
    """Simulate web research for market intelligence (demo mode).

    In production, this would call Bing Search API or similar.
    For the demo, returns plausible mock research results.
    """
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
                "sales_implication": ("Growth tailwind — budget for increased inventory and fulfillment capacity."),
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
                    "Upsell opportunity — new DCs need initial inventory stocking across all categories."
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
                    "Margin improvement — customers may be receptive to volume commitments at current pricing."
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


def _build_function_tool(name: str, description: str, parameters: dict[str, Any]) -> FunctionTool:
    """Create a strict function-tool definition for local Python handlers."""
    return FunctionTool(name=name, description=description, parameters=parameters, strict=True)


def _build_tools(config: OrchestratorConfig) -> tuple[list[ToolDefinition], dict[str, ToolHandler]]:
    """Build the tool list and local function handlers for the prompt agent."""
    tools: list[ToolDefinition] = [
        FabricIQPreviewTool(
            project_connection_id=config.fabric_iq_connection_id,
            require_approval="never",
            name="wwi_sales_data",
            description="Query Wide World Importers sales data warehouse via Fabric Data Agent",
        )
    ]
    handlers: dict[str, ToolHandler] = {
        "forecast_quota": forecast_quota_func,
        "generate_report": generate_report_func,
        "web_research": web_research_func,
        "compute_quota_attainment": compute_attainment_func,
    }

    # Add market data tool if configured.
    if config.market_data_connection_id:
        tools.append(
            FabricIQPreviewTool(
                project_connection_id=config.market_data_connection_id,
                require_approval="never",
                name="real_world_market_data",
                description=(
                    "Query SEC EDGAR financial data for real US public companies — "
                    "revenue, net income, total assets from 10-K/10-Q filings"
                ),
            )
        )

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
            _build_function_tool(
                name="web_research",
                description=(
                    "Search the web for market trends, customer news, and competitive intelligence. "
                    "Returns research findings with citations and sales implications."
                ),
                parameters=WEB_RESEARCH_SCHEMA,
            ),
            _build_function_tool(
                name="compute_quota_attainment",
                description=(
                    "Compute quota attainment metrics: attainment percentage, pipeline coverage, "
                    "run rate projection, and risk rating from provided sales figures."
                ),
                parameters=COMPUTE_ATTAINMENT_SCHEMA,
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
            instructions=_build_agent_instructions(config),
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


def _has_pending_tool_calls(response: ResponsePayload) -> bool:
    """Check whether a response still requests function calls, without executing them."""
    return any(_item_value(item, "type") == "function_call" for item in getattr(response, "output", []) or [])


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

            # Check if the final response still requests tool calls after max rounds
            if round_num >= _MAX_FUNCTION_CALL_ROUNDS and _has_pending_tool_calls(response):
                logger.warning("Agent exceeded %d tool-calling rounds", _MAX_FUNCTION_CALL_ROUNDS)
                return (
                    "The agent exceeded the maximum number of tool-calling rounds. "
                    "Please simplify your request or try again."
                )

            return _extract_output_text(response)
