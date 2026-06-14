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
| `wwi-sales-data` | HTTP | Proxies to Fabric Data Agent endpoint |
| `workiq` | npm (stdio) | Provides M365 activity signals |

### Registration

Tools are registered in `.github/mcp.json` (workspace-scoped) or via `copilot mcp add` (user-scoped):

```json
{
  "mcpServers": {
    "wwi-sales-data": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/workspaces/{id}/dataagent"
    }
  }
}
```

> 📖 [Copilot CLI MCP configuration](https://docs.github.com/copilot/github-copilot-in-the-cli/using-mcp-servers-with-copilot-cli) · [MCP server types](https://modelcontextprotocol.io/docs/concepts/transports)

## HTTP vs stdio transport

MCP supports two primary transports:

| Transport | How it works | Best for |
|---|---|---|
| **HTTP** | Agent makes HTTP requests to a URL | Cloud-hosted services (Fabric, APIs) |
| **stdio** | Agent spawns a local process and communicates via stdin/stdout | Local tools, npm packages |

The Fabric Data Agent uses HTTP (it's a cloud service). WorkIQ uses stdio via npm (it runs as a local process).

## Writing your own MCP server

If you want to add a new tool to the agent, you write an MCP server. The simplest approach:

```python
# Example: a minimal MCP server using the Python SDK
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-tool")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="lookup_customer",
            description="Look up customer information by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer name"}
                },
                "required": ["name"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "lookup_customer":
        # Your logic here
        return [TextContent(type="text", text=f"Customer: {arguments['name']}")]
```

> 📖 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) · [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) · [Building MCP servers](https://modelcontextprotocol.io/docs/guides/building-servers)

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
- [Copilot CLI MCP docs](https://docs.github.com/copilot/github-copilot-in-the-cli/using-mcp-servers-with-copilot-cli)
- [Foundry tool types](https://learn.microsoft.com/azure/ai-foundry/concepts/agents-tools)
