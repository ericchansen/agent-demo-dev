"""Researcher Agent — MCP server that researches companies on the open web."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, ServerRequestContext
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions

from src.agents.mcp_validation import validate_tool_call
from src.agents.researcher.tools import research_company

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_RESEARCH_TOOL = types.Tool(
    name="research_company",
    description=(
        "Research a company on the open web. Returns a summary, recent articles, "
        "and key metrics sourced from news and financial data."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "Name of the company to research.",
            },
            "focus_areas": {
                "type": "string",
                "description": ("Optional focus for the research. One of: news, earnings, strategy, expansion."),
            },
        },
        "required": ["company_name"],
    },
)


async def handle_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    """Advertise available tools."""
    return types.ListToolsResult(tools=[_RESEARCH_TOOL])


async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Dispatch tool calls."""
    if name == "research_company":
        result = await research_company(
            company_name=arguments["company_name"],
            focus_areas=arguments.get("focus_areas"),
        )
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    raise ValueError(f"Unknown tool: {name}")


async def handle_call_tool(ctx: ServerRequestContext, params: types.CallToolRequestParams) -> types.CallToolResult:
    arguments = validate_tool_call(params, [_RESEARCH_TOOL])
    if isinstance(arguments, types.CallToolResult):
        return arguments
    return types.CallToolResult(content=[*await call_tool(params.name, arguments)])


server = Server("researcher-agent", on_list_tools=handle_list_tools, on_call_tool=handle_call_tool)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the Researcher MCP server over stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="researcher-agent",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
