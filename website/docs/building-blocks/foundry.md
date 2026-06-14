---
sidebar_position: 4
title: Azure AI Foundry
---

# Azure AI Foundry

Azure AI Foundry is the production runtime for the agent in this accelerator. It provides agent orchestration, tool registration, identity management, and publishing to M365 Copilot and Teams. If the CLI surface is where you prototype, Foundry is where you deploy.

## Key concepts

### Agent Service
The Foundry Agent Service hosts your agent and manages its lifecycle. It handles:
- **Conversation management** — threads, message history, context windows
- **Tool orchestration** — routing user intent to registered tools
- **Response generation** — combining tool outputs into coherent answers

> 📖 [Agent Service overview](https://learn.microsoft.com/azure/ai-foundry/concepts/agents)

### Responses API
The Responses API is how the agent calls tools and generates responses. It supports:
- **Function calling** — the agent decides which tools to call based on user intent
- **Streaming** — progressive output for long-running operations
- **Structured output** — JSON responses for programmatic consumption

> 📖 [Responses API reference](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-responses)

### Platform tools vs function tools

| Type | Description | Example |
|---|---|---|
| **Platform tool** | First-party Microsoft tools with built-in auth | FabricIQPreviewTool, WorkIQPreviewTool |
| **Function tool** | Custom code you write and register | Report generator, forecast calculator |
| **Code interpreter** | Built-in Python sandbox for data analysis | Ad-hoc calculations, chart generation |

Platform tools handle authentication and data access automatically. Function tools give you full control over logic and output.

> 📖 [Tool types](https://learn.microsoft.com/azure/ai-foundry/concepts/agents-tools) · [Function calling](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-function-calling) · [Code interpreter](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-code-interpreter)

### Agent Applications
An Agent Application is a published agent with:
- **Entra identity** — its own app registration for auth
- **Stable endpoint** — accessible from M365 Copilot, Teams, or direct API
- **RBAC** — control who can discover and use the agent
- **Monitoring** — usage metrics, error tracking, cost attribution

> 📖 [Publishing agents](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-publish) · [Agent monitoring](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-monitor)

## How it fits in this accelerator

The Foundry surface (`src/orchestrator/`) registers three tools:

1. **FabricIQPreviewTool** — wraps the same Fabric Data Agent endpoint used by the CLI's `wwi-sales-data` MCP server
2. **WorkIQPreviewTool** — wraps WorkIQ with OBO authentication
3. **Report generator function** — produces DOCX, uploads to OneDrive, returns download link

The agent's system prompt encodes the orchestration logic — when to call which tool, how to combine results, and how to format output.

## CLI → Foundry translation

| What you did in CLI | How it maps to Foundry |
|---|---|
| Added an MCP server | Register a platform/function tool |
| Wrote a skill | Encode workflow in agent system prompt |
| Tested with `copilot` | Test in Foundry playground |
| Shared via `.github/mcp.json` | Publish as Agent Application |

The mental model: CLI is your workbench, Foundry is your factory.

## Further reading

- [Azure AI Foundry overview](https://learn.microsoft.com/azure/ai-foundry/what-is-ai-foundry)
- [Agent Service concepts](https://learn.microsoft.com/azure/ai-foundry/concepts/agents)
- [Creating agents](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-create)
- [Agent tools](https://learn.microsoft.com/azure/ai-foundry/concepts/agents-tools)
- [Publishing to M365](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-publish)
- [Foundry pricing](https://learn.microsoft.com/azure/ai-foundry/concepts/pricing)
