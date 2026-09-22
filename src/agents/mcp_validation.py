"""Explicit input validation shared by the lowlevel MCP servers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from jsonschema import ValidationError, validate
from mcp.types import CallToolRequestParams, CallToolResult, TextContent, Tool


def tool_error(message: str) -> CallToolResult:
    """Return a tool failure rather than a successful text payload."""
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


def validate_tool_call(params: CallToolRequestParams, tools: Sequence[Tool]) -> dict[str, Any] | CallToolResult:
    """Validate against the same schema advertised by tools/list before dispatch."""
    tool = next((tool for tool in tools if tool.name == params.name), None)
    if tool is None:
        return tool_error(f"Unknown tool: {params.name}")

    arguments = params.arguments or {}
    try:
        validate(instance=arguments, schema=tool.input_schema)
    except ValidationError as exc:
        return tool_error(f"Input validation error: {exc.message}")
    return arguments
