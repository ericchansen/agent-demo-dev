"""Hosted Agent for Azure AI Foundry using GitHub Copilot SDK.

This module implements a bring-your-own-code agent that runs as a container
in Foundry's managed runtime. It uses the GitHub Copilot SDK for model
interaction and the azure-ai-agentserver-invocations package to receive
requests from the Foundry invocation protocol.

Architecture:
  Foundry Runtime → HTTP invocation → this server → Copilot SDK → tools → response

Tools available:
  - fabric_query: Query WWI sales data via Fabric Data Agent
  - web_research: Search for market intelligence and customer news
  - compute_attainment: Calculate quota attainment metrics
  - generate_report: Produce formatted DOCX/Excel artifacts
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FABRIC_MCP_URL = os.environ.get(
    "FABRIC_MCP_URL",
    "https://api.fabric.microsoft.com/v1/mcp/workspaces/"
    "6cf857b8-a0d0-4029-af88-62a83b4116e5/dataagents/"
    "f89ca52e-8d23-4020-b0ab-489ab57d0d14/agent",
)
MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "")
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT", "gpt-4o")

SYSTEM_PROMPT = """You are a sales analyst for Wide World Importers (WWI).

You have access to:
1. Fabric Data Agent — query structured sales data (revenue, customers, products, geography)
2. Web Research — find market trends, customer news, competitive intelligence
3. Quota Attainment — compute pipeline coverage, run rate, and risk rating
4. Report Generation — produce formatted DOCX/Excel output files

Always cite data sources. Use markdown tables for structured data.
Proactively surface insights the user might not have asked for."""


# ---------------------------------------------------------------------------
# Tool definitions (Copilot SDK format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fabric_query",
            "description": (
                "Query the WWI sales data warehouse via Fabric Data Agent. "
                "Ask natural language questions about sales, customers, products, and geography."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question about WWI sales data.",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_research",
            "description": "Search for market trends, customer news, and competitive intelligence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "customer_name": {"type": "string", "description": "Optional customer context."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_attainment",
            "description": "Compute quota attainment metrics from sales figures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "annual_target": {"type": "number"},
                    "ytd_actual": {"type": "number"},
                    "open_pipeline": {"type": "number"},
                    "months_elapsed": {"type": "number"},
                    "days_elapsed": {"type": "number"},
                },
                "required": ["annual_target", "ytd_actual", "open_pipeline", "months_elapsed", "days_elapsed"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def handle_fabric_query(arguments: dict[str, Any]) -> dict[str, Any]:
    """Forward a natural language question to the Fabric Data Agent MCP endpoint."""
    # In the hosted agent, we use managed identity tokens instead of az CLI
    question = arguments.get("question", "")
    logger.info("Fabric query: %s", question[:100])

    # TODO: Implement actual MCP call using managed identity
    # For now, return a placeholder that indicates the tool is wired
    return {
        "status": "not_implemented",
        "message": (
            "Fabric MCP integration pending managed identity setup. "
            f"Query was: {question}"
        ),
    }


def handle_web_research(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute web research (demo mode returns mock data)."""
    from src.orchestrator.foundry_agent import web_research_func

    return web_research_func(arguments)


def handle_compute_attainment(arguments: dict[str, Any]) -> dict[str, Any]:
    """Compute quota attainment metrics."""
    from src.orchestrator.foundry_agent import compute_attainment_func

    return compute_attainment_func(arguments)


TOOL_HANDLERS: dict[str, Any] = {
    "fabric_query": handle_fabric_query,
    "web_research": handle_web_research,
    "compute_attainment": handle_compute_attainment,
}


# ---------------------------------------------------------------------------
# Agent entry point (Foundry invocation protocol)
# ---------------------------------------------------------------------------


def process_invocation(user_message: str) -> str:
    """Process a single user message through the agent pipeline.

    This is the main entry point called by the Foundry invocation server.
    In a full implementation, this would:
    1. Initialize a Copilot SDK client
    2. Send the user message with system prompt and tools
    3. Execute tool calls in a loop
    4. Return the final response

    For now, this scaffolds the flow and documents the integration points.
    """
    logger.info("Processing: %s", user_message[:100])

    # Placeholder for Copilot SDK integration:
    #
    # from github_copilot import CopilotClient
    #
    # client = CopilotClient(endpoint=MODEL_ENDPOINT)
    # response = client.chat.completions.create(
    #     model=MODEL_DEPLOYMENT,
    #     messages=[
    #         {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "user", "content": user_message},
    #     ],
    #     tools=TOOLS,
    # )
    #
    # # Tool execution loop
    # while response.choices[0].finish_reason == "tool_calls":
    #     tool_calls = response.choices[0].message.tool_calls
    #     tool_results = []
    #     for tc in tool_calls:
    #         handler = TOOL_HANDLERS.get(tc.function.name)
    #         args = json.loads(tc.function.arguments)
    #         result = handler(args) if handler else {"error": f"Unknown: {tc.function.name}"}
    #         tool_results.append({"tool_call_id": tc.id, "content": json.dumps(result)})
    #     response = client.chat.completions.create(
    #         model=MODEL_DEPLOYMENT,
    #         messages=[...previous + tool_results],
    #         tools=TOOLS,
    #     )

    return (
        f"[Hosted Agent scaffold] Received: '{user_message[:80]}...'\n\n"
        "This agent is scaffolded with tool definitions and handlers. "
        "Full Copilot SDK integration requires:\n"
        "1. `pip install github-copilot-sdk azure-ai-agentserver-invocations`\n"
        "2. Model endpoint configuration\n"
        "3. Managed identity for Fabric MCP access\n"
        "4. Dockerfile + deployment to Foundry managed runtime"
    )


if __name__ == "__main__":
    # Quick local test
    result = process_invocation("What are the top 5 customers by revenue?")
    print(result)
