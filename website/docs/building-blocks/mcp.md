---
sidebar_position: 3
title: MCP (Model Context Protocol)
---

# Model Context Protocol (MCP)

MCP is the wire protocol that connects agents to tools. It defines how an agent discovers what tools are available, what inputs they expect, and how to call them. In this accelerator, MCP is the bridge between Copilot CLI and backend services like the Fabric Data Agent and WorkIQ.

## Why MCP matters

Before MCP, every agent framework had its own way of defining tools — different schemas, different calling conventions, different discovery mechanisms. MCP standardizes this:

- **Tool discovery** — the agent asks "what can you do?" and gets a structured list
- **Typed inputs/outputs** — JSON Schema for parameters and return values
- **Transport-agnostic** — works over HTTP, stdio, WebSocket
- **Server-side logic** — the tool implementation lives in the server, not the agent

This means you can write a tool server once and connect it to any MCP-compatible agent.

> 📖 [MCP specification](https://modelcontextprotocol.io/) · [MCP concepts: tools](https://modelcontextprotocol.io/docs/concepts/tools)

## MCP in this accelerator

### Tool servers

| Server | Transport | What it does |
|---|---|---|
| `fabric-core` | HTTP | Fabric workspace and item operations |
| `wwi-sales-data` | HTTP | Fabric Data Agent — WWI sales Lakehouse |
| `market-data` | HTTP | Fabric Data Agent — SEC EDGAR financials |
| `researcher-agent` | stdio | Web search for market intelligence |
| `sharepoint-agent` | stdio | SharePoint / Graph document access |
| `report-generator` | stdio | DOCX and PPTX reports with citations |
| `quota-estimator` | stdio | XLSX, HTML, and PDF quota reports |

These names match the repository's three MCP registries. WorkIQ is an optional user-scoped integration; the demo tenant uses mocked M365 activity context.

### Registration

Tools are registered in `.github/mcp.json` (workspace-scoped) or via `copilot mcp add` (user-scoped):

```json
{
  "mcpServers": {
    "wwi-sales-data": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/workspaces/<WORKSPACE_ID>/dataagents/<DATA_AGENT_ID>/agent"
    }
  }
}
```

> 📖 [Copilot CLI MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) · [MCP server types](https://modelcontextprotocol.io/docs/concepts/transports)

## HTTP vs stdio transport

MCP supports two primary transports:

| Transport | How it works | Best for |
|---|---|---|
| **HTTP** | Agent makes HTTP requests to a URL | Cloud-hosted services (Fabric, APIs) |
| **stdio** | Agent spawns a local process and communicates via stdin/stdout | Local tools, npm packages |

The Fabric Data Agent uses HTTP (it's a cloud service). WorkIQ uses stdio via npm (it runs as a local process).

## Writing your own MCP server

The local servers use the [MCP Python SDK 2 migration API](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/docs/migration.md): typed callbacks passed to `Server`, rather than the SDK 1 decorators. In Python, tool schemas use `input_schema`; discovery responses still serialize the protocol field as `inputSchema`.

SDK 2 does not automatically validate tool arguments against the advertised JSON Schema. Inside this repository, reuse `validate_tool_call` so malformed inputs are rejected **before** your handler creates files, acquires tokens, or calls external services:

```python
import asyncio

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from src.agents.mcp_validation import validate_tool_call

TOOLS = [
    Tool(
        name="lookup_customer",
        description="Echo a demo customer name without contacting a backend",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Customer name"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    )
]


async def list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


async def call_tool(ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
    arguments = validate_tool_call(params, TOOLS)
    if isinstance(arguments, CallToolResult):
        return arguments
    return CallToolResult(content=[TextContent(type="text", text=f"Customer: {arguments['name']}")])


server = Server("my-tool", on_list_tools=list_tools, on_call_tool=call_tool)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

> 📖 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) · [Build with MCP agent skills](https://modelcontextprotocol.io/docs/develop/build-with-agent-skills.md)

## Compatibility and verification

The project supports `mcp>=2.2.0,<3` and declares `jsonschema>=4.20,<5` directly. The validator preserves the existing schemas, including open nested objects and tools that allow extra properties. It does not insert JSON Schema defaults into arguments.

| Boundary | Expected behavior |
|---|---|
| Missing, null, or empty argument map | Validate as an empty object; missing required properties return a tool result with `isError: true`. |
| Wrong property type or disallowed extra property | Return `Input validation error: ...` without entering the business handler. |
| Unknown tool name | Return `Unknown tool: ...` with `isError: true`, even before tool discovery. |
| Scalar/list argument map or invalid tool-name type | JSON-RPC invalid-parameters error (`-32602`), not a tool result. |
| Unknown JSON-RPC method | SDK 2 returns method-not-found (`-32601`); SDK 1 returned `-32602`. This SDK behavior change is intentional. |
| Malformed JSON or malformed outer envelope | Reject at the transport boundary. Tests verify recovery to subsequent valid requests rather than waiting for a correlated reply to a malformed envelope. |

The raw-wire tests cover both `2024-11-05` and the SDK's latest **handshake** version. The latest per-request protocol version is not interchangeable with the handshake version. Python `CallToolResult` dumps can contain `resultType`; older negotiated wire formats omit that field.

```powershell
uv sync --locked --extra dev
uv run --no-sync pytest tests/unit/test_mcp_validation.py tests/integration/test_mcp_servers.py
uv run --no-sync python scripts/demo_check.py
```

Readiness checks verify registry consistency, start all four local entrypoints with the installed interpreter, and discover their five tools through the real SDK client. Research and SharePoint startup checks use mock mode; this does not prove live Fabric, Databricks, Graph, or Foundry connectivity. CI keeps fresh pip installation checks alongside a locked-uv lane.

The optional Databricks managed-MCP transport requires `databricks-mcp>=0.9.2`; the previously locked 0.9.0 client imports the SDK 1 transport name removed in MCP 2. Its explicit smoke target uses the real installed client and auth/transport code with controlled HTTP responses and synthetic credentials, not live workspace access:

```powershell
uv sync --locked --extra dev --extra databricks-mcp
uv run --no-sync pytest tests/optional/databricks_mcp_smoke.py
```

Optional smoke targets fail on missing dependencies instead of silently skipping. The SDK-direct Genie path does not require this extra. The [Foundry architecture guide](../architecture/foundry-surface) documents the separate Agent Framework extra and its real-client construction check.

## MCP vs Foundry tools

MCP is the protocol used in the CLI surface. In the Foundry surface, the same capabilities are registered as Foundry tool types:

| MCP Concept | Foundry Equivalent |
|---|---|
| MCP server | Platform tool or function tool |
| Tool discovery (list_tools) | Tool registration in agent config |
| Tool call (call_tool) | Function calling via Responses API |

The key difference: MCP is a runtime discovery protocol (the agent asks "what tools exist?"), while Foundry tools are registered at agent creation time.

## Further reading

- [MCP specification](https://modelcontextprotocol.io/)
- [MCP concepts: tools](https://modelcontextprotocol.io/docs/concepts/tools)
- [MCP concepts: transports](https://modelcontextprotocol.io/docs/concepts/transports)
- [Copilot CLI MCP docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [Foundry function calling](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling)
