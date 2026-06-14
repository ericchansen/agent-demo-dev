"""Hosted Agent runtime for Azure AI Foundry managed containers."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

from src.agents.quota_estimator.pipeline import demo_research_data, demo_sales_rows, demo_workiq_activity
from src.orchestrator.fabric_mcp_client import FabricMcpClient, FabricMcpConfigurationError, FabricMcpError
from src.orchestrator.tool_runtime import (
    ACCOUNT_ACTIVITY_SCHEMA,
    COMPUTE_ATTAINMENT_SCHEMA,
    FORECAST_QUOTA_SCHEMA,
    GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA,
    GENERATE_REPORT_SCHEMA,
    WEB_RESEARCH_SCHEMA,
    compute_attainment_func,
    forecast_quota_func,
    generate_quota_estimation_report_func,
    generate_report_func,
    mock_workiq_func,
    web_research_func,
)

logger = logging.getLogger(__name__)

MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "")
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT", "gpt-4o")
_MAX_TOOL_CALL_ROUNDS = 15

SYSTEM_PROMPT = """You are a sales analyst for Wide World Importers (WWI).

You have access to:
1. Fabric Data Agent - query structured sales data (revenue, customers, products, geography)
2. Web Research - find market trends, customer news, competitive intelligence
3. Quota Attainment - compute pipeline coverage, run rate, and risk rating
4. Report Generation - produce formatted DOCX, XLSX, HTML, and PDF output files

Always cite data sources. Use markdown tables for structured data.
Proactively surface insights the user might not have asked for."""


class HostedChatAdapter(Protocol):
    """Minimal chat-completion adapter used by the hosted runtime."""

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return a chat response containing content and optional tool calls."""


def _function_tool(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


TOOLS = [
    _function_tool(
        "fabric_query",
        "Query the WWI sales data warehouse via Fabric Data Agent MCP.",
        {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about WWI sales data.",
                }
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    ),
    _function_tool(
        "forecast_quota",
        "Return a structured FY quota projection payload.",
        FORECAST_QUOTA_SCHEMA,
    ),
    _function_tool(
        "generate_quota_estimation_report",
        "Generate XLSX, HTML, and PDF quota estimation artifacts.",
        GENERATE_QUOTA_ESTIMATION_REPORT_SCHEMA,
    ),
    _function_tool(
        "generate_report",
        "Generate a formatted DOCX sales report for a customer account.",
        GENERATE_REPORT_SCHEMA,
    ),
    _function_tool(
        "web_research",
        "Search for market trends, customer news, and competitive intelligence.",
        WEB_RESEARCH_SCHEMA,
    ),
    _function_tool(
        "compute_quota_attainment",
        "Compute quota attainment, pipeline coverage, run-rate projection, and risk rating.",
        COMPUTE_ATTAINMENT_SCHEMA,
    ),
    _function_tool(
        "get_account_activity",
        "Retrieve recent M365 activity signals for a customer account.",
        ACCOUNT_ACTIVITY_SCHEMA,
    ),
]


def handle_fabric_query(arguments: dict[str, Any]) -> dict[str, Any]:
    """Forward a natural-language question to the configured Fabric Data Agent MCP endpoint."""
    question = str(arguments.get("question", "")).strip()
    logger.info("Fabric query: %s", question[:100])
    try:
        return FabricMcpClient.from_env().query(question)
    except FabricMcpConfigurationError as exc:
        return {
            "status": "configuration_error",
            "message": str(exc),
            "required_environment": ["FABRIC_MCP_URL", "FABRIC_MCP_TOOL_NAME"],
            "question": question,
        }
    except FabricMcpError as exc:
        return {"status": "error", "message": str(exc), "question": question}


def handle_forecast_quota(arguments: dict[str, Any]) -> dict[str, Any]:
    """Run the shared deterministic quota forecast."""
    return forecast_quota_func(arguments)


def handle_generate_quota_estimation_report(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate quota estimation artifacts with shared local logic."""
    return generate_quota_estimation_report_func(arguments)


def handle_generate_report(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate a DOCX report with shared local logic."""
    return generate_report_func(arguments)


def handle_web_research(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute demo-safe market research."""
    return web_research_func(arguments)


def handle_compute_quota_attainment(arguments: dict[str, Any]) -> dict[str, Any]:
    """Compute quota attainment metrics."""
    return compute_attainment_func(arguments)


def handle_get_account_activity(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return demo-safe M365 activity context."""
    return mock_workiq_func(arguments)


TOOL_HANDLERS = {
    "fabric_query": handle_fabric_query,
    "forecast_quota": handle_forecast_quota,
    "generate_quota_estimation_report": handle_generate_quota_estimation_report,
    "generate_report": handle_generate_report,
    "web_research": handle_web_research,
    "compute_quota_attainment": handle_compute_quota_attainment,
    "get_account_activity": handle_get_account_activity,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one hosted tool by name."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown hosted agent tool: {name}")
    return handler(arguments)


def process_invocation(user_message: str, adapter: HostedChatAdapter | None = None) -> str:
    """Process a single Foundry hosted-agent invocation."""
    logger.info("Processing hosted invocation: %s", user_message[:100])
    if adapter is not None:
        return _process_with_adapter(user_message, adapter)
    return _process_with_local_runtime(user_message)


def _process_with_adapter(user_message: str, adapter: HostedChatAdapter) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for _round_num in range(1, _MAX_TOOL_CALL_ROUNDS + 1):
        response = adapter.complete(messages, TOOLS)
        tool_calls = _extract_tool_calls(response)
        content = str(response.get("content", "") or "")
        if not tool_calls:
            return content

        messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
        for tool_call in tool_calls:
            name = _tool_call_name(tool_call)
            arguments = _tool_call_arguments(tool_call)
            result = execute_tool(name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(tool_call.get("id", name)),
                    "name": name,
                    "content": json.dumps(result),
                }
            )

    return "The hosted agent reached the tool-call safety limit before producing a final answer."


def _process_with_local_runtime(user_message: str) -> str:
    message = user_message.lower()
    customer_name = _extract_customer_name(user_message)

    if "quota" in message and any(term in message for term in ("report", "estimate", "estimation", "artifact")):
        output_dir = os.environ.get("HOSTED_AGENT_OUTPUT_DIR", "output/hosted-agent")
        result = handle_generate_quota_estimation_report(
            {
                "customer_name": customer_name,
                "sales_rows": demo_sales_rows(),
                "research_data": demo_research_data(customer_name),
                "workiq_activity": demo_workiq_activity(customer_name),
                "scenario": "base",
                "output_dir": output_dir,
                "formats": ["xlsx", "html", "pdf"],
            }
        )
        artifacts = result.get("artifacts", {})
        return (
            f"Generated a quota estimation report for {customer_name}.\n\n"
            f"Summary: {json.dumps(result.get('summary', {}), indent=2)}\n\n"
            f"Artifacts: {json.dumps(artifacts, indent=2)}"
        )

    if "attainment" in message or "pipeline coverage" in message:
        result = handle_compute_quota_attainment(
            {
                "annual_target": 1_200_000,
                "ytd_actual": 590_000,
                "open_pipeline": 950_000,
                "months_elapsed": 6,
                "days_elapsed": 180,
            }
        )
        return f"Quota attainment snapshot:\n\n```json\n{json.dumps(result, indent=2)}\n```"

    if "forecast" in message or "quota" in message:
        result = handle_forecast_quota({"customer_name": customer_name, "scenario": "base"})
        return f"Quota forecast for {customer_name}:\n\n```json\n{json.dumps(result, indent=2)}\n```"

    if "research" in message or "market" in message or "news" in message:
        result = handle_web_research({"query": user_message, "customer_name": customer_name})
        return f"Market research for {customer_name}:\n\n```json\n{json.dumps(result, indent=2)}\n```"

    if any(term in message for term in ("sales", "revenue", "customer", "product", "territory")):
        result = handle_fabric_query({"question": user_message})
        return f"Fabric query result:\n\n```json\n{json.dumps(result, indent=2)}\n```"

    return (
        "Hosted WWI sales agent is ready. Ask for Fabric sales analysis, market research, "
        "quota forecasts, quota estimation artifacts, quota attainment, account activity, or report generation."
    )


def _extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw_tool_calls = response.get("tool_calls", [])
    if not isinstance(raw_tool_calls, list):
        raise ValueError("adapter response tool_calls must be a list.")
    return [item for item in raw_tool_calls if isinstance(item, dict)]


def _tool_call_name(tool_call: dict[str, Any]) -> str:
    function = tool_call.get("function")
    if isinstance(function, dict):
        name = function.get("name")
    else:
        name = tool_call.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("tool call is missing function name.")
    return name


def _tool_call_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function")
    raw_arguments = function.get("arguments") if isinstance(function, dict) else tool_call.get("arguments", {})
    if isinstance(raw_arguments, str):
        parsed = json.loads(raw_arguments)
    else:
        parsed = raw_arguments
    if not isinstance(parsed, dict):
        raise ValueError("tool call arguments must be a JSON object.")
    return parsed


def _extract_customer_name(user_message: str) -> str:
    for marker in (" for ", " about "):
        if marker in user_message.lower():
            suffix = user_message.lower().split(marker, maxsplit=1)[1]
            words = suffix.replace("?", "").replace(".", "").split()
            if words:
                return " ".join(word.capitalize() for word in words[:3])
    return "Wide World Importers"


if __name__ == "__main__":
    print(process_invocation("Generate a quota report for Tailspin Toys"))
