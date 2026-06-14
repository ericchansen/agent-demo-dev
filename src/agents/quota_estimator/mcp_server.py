"""Quota Estimator MCP server for generating XLSX, HTML, and PDF artifacts."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.agents.quota_estimator.pipeline import generate_quota_estimation_report

server = Server("quota-estimator")


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[Tool]:
    """Advertise quota estimation report generation."""
    return [
        Tool(
            name="generate_quota_estimation_report",
            description=(
                "Generate quota estimate artifacts from Fabric WWI historical sales rows, "
                "market research context, and WorkIQ activity signals. Returns XLSX, HTML, "
                "and PDF file paths by default."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer account name."},
                    "sales_rows": {
                        "type": "array",
                        "description": (
                            "Rows from SalesOrderHeader joined to SalesTerritory. Each row needs territory, "
                            "order_date, revenue, and optionally category and quantity."
                        ),
                        "items": {"type": "object", "additionalProperties": True},
                    },
                    "research_data": {
                        "type": "object",
                        "description": "Market research payload from researcher-agent or Copilot /research.",
                        "additionalProperties": True,
                    },
                    "workiq_activity": {
                        "type": "object",
                        "description": "WorkIQ or synthetic M365 activity context.",
                        "additionalProperties": True,
                    },
                    "scenario": {
                        "type": "string",
                        "enum": ["conservative", "base", "aggressive"],
                        "default": "base",
                        "description": "Deterministic forecast scenario applied to recommended growth.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory where generated report artifacts should be written.",
                    },
                    "formats": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["xlsx", "html", "pdf"]},
                        "default": ["xlsx", "html", "pdf"],
                    },
                },
                "required": ["customer_name", "sales_rows"],
                "additionalProperties": False,
            },
        )
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch quota estimator MCP tool calls."""
    if name != "generate_quota_estimation_report":
        raise ValueError(f"Unknown tool: {name}")

    customer_name = str(arguments["customer_name"])
    sales_rows_raw = arguments["sales_rows"]
    if not isinstance(sales_rows_raw, list) or not all(isinstance(item, dict) for item in sales_rows_raw):
        raise ValueError("sales_rows must be a list of objects.")

    research_data = arguments.get("research_data")
    if research_data is not None and not isinstance(research_data, dict):
        raise ValueError("research_data must be an object when provided.")

    workiq_activity = arguments.get("workiq_activity")
    if workiq_activity is not None and not isinstance(workiq_activity, dict):
        raise ValueError("workiq_activity must be an object when provided.")

    formats_raw = arguments.get("formats")
    if formats_raw is not None and not isinstance(formats_raw, list):
        raise ValueError("formats must be a list of strings when provided.")

    scenario = arguments.get("scenario")
    if scenario is not None and not isinstance(scenario, str):
        raise ValueError("scenario must be a string when provided.")

    result = generate_quota_estimation_report(
        customer_name=customer_name,
        sales_rows=sales_rows_raw,
        research_data=research_data,
        workiq_activity=workiq_activity,
        scenario=scenario if scenario is not None else "base",
        output_dir=str(arguments.get("output_dir", "output/quota-estimates")),
        formats=[str(item) for item in formats_raw] if formats_raw is not None else None,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    """Run the quota estimator MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
