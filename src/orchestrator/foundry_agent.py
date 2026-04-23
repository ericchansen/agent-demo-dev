"""Azure AI Foundry orchestrator — creates a sales agent with Fabric + custom tools.

This module registers a FabricTool for NL→SQL data queries and custom function
stubs for web research, SharePoint search, and report generation.

Usage:
    from src.orchestrator.foundry_agent import create_sales_agent, run_query

    agent, project_client = create_sales_agent()
    answer = run_query(project_client, agent, "What were total sales last quarter?")
"""

from __future__ import annotations

import json
import time
from typing import Any

from azure.ai.agents.models import (
    FabricTool,
    FunctionTool,
    MessageRole,
    RunStatus,
    ToolSet,
)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from src.orchestrator.config import OrchestratorConfig

# ---------------------------------------------------------------------------
# Custom function definitions (tool schemas for the LLM)
# ---------------------------------------------------------------------------

_CUSTOM_FUNCTIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "research_customer",
            "description": (
                "Search the web for recent news, financials, and competitive "
                "intelligence about a customer or prospect."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Name of the company to research.",
                    },
                    "focus_areas": {
                        "type": "string",
                        "description": (
                            "Comma-separated areas of interest "
                            "(e.g. 'financials, competitors, recent news')."
                        ),
                    },
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_sharepoint",
            "description": (
                "Search the organization's SharePoint sites for internal "
                "documents, policies, presentations, and meeting notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for SharePoint content.",
                    },
                    "site_filter": {
                        "type": "string",
                        "description": "Optional SharePoint site URL to scope the search.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": (
                "Generate a formatted report document (DOCX or PPTX) from "
                "provided content sections."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Report title.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["docx", "pptx"],
                        "description": "Output format: 'docx' or 'pptx'.",
                    },
                    "sections": {
                        "type": "string",
                        "description": (
                            "JSON-encoded list of section objects, each with "
                            "'heading' and 'content' keys."
                        ),
                    },
                },
                "required": ["title", "format", "sections"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Custom function implementations (stubs)
# ---------------------------------------------------------------------------


def research_customer_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Search the web for customer/competitor intelligence.

    TODO: Replace stub with real implementation using Bing Search API,
    Tavily, or another search provider.
    """
    company = arguments.get("company_name", "Unknown")
    focus = arguments.get("focus_areas", "general")
    # TODO: Replace stubs with real implementations
    return {
        "company": company,
        "focus_areas": focus,
        "results": [
            {
                "title": f"[Stub] Recent news about {company}",
                "snippet": "This is a placeholder. Implement web search to get real results.",
                "url": "https://example.com",
            }
        ],
        "source": "stub — replace with real search provider",
    }


def search_sharepoint_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Search SharePoint for internal documents.

    TODO: Replace stub with real implementation using Microsoft Graph API
    Search endpoint (/search/query).
    """
    query = arguments.get("query", "")
    site_filter = arguments.get("site_filter", "")
    # TODO: Replace stubs with real implementations
    return {
        "query": query,
        "site_filter": site_filter,
        "results": [
            {
                "title": f"[Stub] SharePoint result for '{query}'",
                "snippet": "This is a placeholder. Implement Graph API search.",
                "url": "https://contoso.sharepoint.com",
            }
        ],
        "source": "stub — replace with Graph API /search/query",
    }


def generate_report_func(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate a DOCX or PPTX report from provided sections.

    TODO: Replace stub with real implementation using python-docx
    (for DOCX) or python-pptx (for PPTX).
    """
    title = arguments.get("title", "Untitled Report")
    fmt = arguments.get("format", "docx")
    sections_raw = arguments.get("sections", "[]")

    try:
        sections = json.loads(sections_raw) if isinstance(sections_raw, str) else sections_raw
    except json.JSONDecodeError:
        sections = []

    # TODO: Replace stubs with real implementations
    return {
        "title": title,
        "format": fmt,
        "section_count": len(sections),
        "file_path": f"/output/{title.replace(' ', '_').lower()}.{fmt}",
        "source": "stub — replace with python-docx / python-pptx generation",
    }


# Map function names to implementations
_FUNCTION_MAP: dict[str, Any] = {
    "research_customer": research_customer_func,
    "search_sharepoint": search_sharepoint_func,
    "generate_report": generate_report_func,
}


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------


def create_sales_agent(
    config: OrchestratorConfig | None = None,
) -> tuple[Any, AIProjectClient]:
    """Create an Azure AI Foundry agent with FabricTool + custom functions.

    Args:
        config: Orchestrator config. If None, loads from environment.

    Returns:
        Tuple of (agent, project_client).
    """
    if config is None:
        config = OrchestratorConfig.from_env()

    credential = DefaultAzureCredential()
    project_client = AIProjectClient.from_connection_string(
        conn_str=config.foundry_project_connection,
        credential=credential,
    )

    # Fabric Data Agent tool (NL→SQL)
    fabric_tool = FabricTool(fabric_connection_id=config.fabric_connection_id)

    # Custom function tools (web research, SharePoint, reports)
    function_tool = FunctionTool(functions=_CUSTOM_FUNCTIONS)

    toolset = ToolSet()
    toolset.add(fabric_tool)
    toolset.add(function_tool)

    agent = project_client.agents.create_agent(
        model=config.model_deployment_name,
        name="WWI Sales Agent",
        instructions=(
            "You are a sales analyst for Wide World Importers. "
            "Use the Fabric data tool to answer questions about sales, "
            "customers, and inventory. Use research_customer for web-based "
            "competitive intelligence. Use search_sharepoint for internal "
            "documents. Use generate_report to create formatted deliverables. "
            "Always cite your data sources."
        ),
        toolset=toolset,
    )

    return agent, project_client


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------


def run_query(
    project_client: AIProjectClient,
    agent: Any,
    question: str,
    *,
    poll_interval: float = 1.0,
    max_wait: float = 120.0,
) -> str:
    """Send a question to the agent and return the final answer.

    Creates a new thread, posts the user message, runs the agent,
    polls for completion, and returns the assistant's response text.

    Args:
        project_client: Authenticated Foundry project client.
        agent: The created agent object.
        question: User's natural-language question.
        poll_interval: Seconds between polling attempts.
        max_wait: Maximum seconds to wait for completion.

    Returns:
        The assistant's response text.

    Raises:
        TimeoutError: If the run doesn't complete within max_wait.
        RuntimeError: If the run fails.
    """
    thread = project_client.agents.threads.create()

    project_client.agents.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=question,
    )

    run = project_client.agents.runs.create(
        thread_id=thread.id,
        agent_id=agent.id,
    )

    # Poll for completion
    elapsed = 0.0
    while elapsed < max_wait:
        run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)

        if run.status == RunStatus.COMPLETED:
            break
        if run.status in (RunStatus.FAILED, RunStatus.CANCELLED):
            raise RuntimeError(f"Agent run {run.status}: {getattr(run, 'last_error', 'unknown')}")
        if run.status == RunStatus.REQUIRES_ACTION:
            _handle_tool_calls(project_client, thread.id, run)

        time.sleep(poll_interval)
        elapsed += poll_interval
    else:
        raise TimeoutError(f"Agent run did not complete within {max_wait}s")

    # Retrieve assistant messages
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for msg in reversed(messages.data):
        if msg.role == MessageRole.ASSISTANT:
            return msg.content[0].text.value if msg.content else "(no response)"

    return "(no assistant response found)"


def _handle_tool_calls(
    project_client: AIProjectClient,
    thread_id: str,
    run: Any,
) -> None:
    """Process required tool calls by dispatching to local function stubs."""
    tool_calls = run.required_action.submit_tool_outputs.tool_calls
    tool_outputs = []

    for call in tool_calls:
        func_name = call.function.name
        func_args = json.loads(call.function.arguments)

        handler = _FUNCTION_MAP.get(func_name)
        if handler:
            result = handler(func_args)
        else:
            result = {"error": f"Unknown function: {func_name}"}

        tool_outputs.append(
            {
                "tool_call_id": call.id,
                "output": json.dumps(result),
            }
        )

    project_client.agents.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run.id,
        tool_outputs=tool_outputs,
    )
