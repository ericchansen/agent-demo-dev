"""SharePoint Agent — MCP server for document retrieval via Microsoft Graph API."""

from __future__ import annotations

import asyncio
import logging
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.agents.sharepoint.tools import get_document_content, search_documents

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

server = Server("sharepoint-agent")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Advertise available tools to the MCP client."""
    return [
        Tool(
            name="search_documents",
            description=(
                "Search SharePoint for documents matching a query string. "
                "Returns a list of matching documents with name, URL, excerpt, and last-modified date."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text search query to find documents.",
                    },
                    "site_id": {
                        "type": "string",
                        "description": "Optional SharePoint site ID to scope the search.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_document_content",
            description=(
                "Retrieve the full text content of a specific SharePoint document "
                "identified by its drive ID and item ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "drive_id": {
                        "type": "string",
                        "description": "The OneDrive/SharePoint drive ID containing the document.",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "The unique item ID of the document within the drive.",
                    },
                },
                "required": ["drive_id", "item_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch MCP tool calls to the appropriate handler."""
    import json  # noqa: PLC0415

    if name == "search_documents":
        query: str = arguments["query"]
        site_id: str | None = arguments.get("site_id")
        results = await search_documents(query, site_id=site_id)
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    if name == "get_document_content":
        drive_id: str = arguments["drive_id"]
        item_id: str = arguments["item_id"]
        result = await get_document_content(drive_id, item_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the SharePoint MCP server over stdio."""
    mode = os.environ.get("SHAREPOINT_MODE", "mock")
    logger.info("Starting SharePoint Agent MCP server (mode=%s)", mode)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
