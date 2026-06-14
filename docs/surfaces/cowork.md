# Cowork (M365 Plugin Surface)

> **Status:** 📋 Documented — requires Frontier preview enrollment

## Overview

Cowork is Microsoft's agent-native work surface within M365. It runs
plugins in a managed environment with **native WorkIQ access** — the one
data source we cannot easily access from CLI or Foundry today.

## Architecture Mapping

The Cowork plugin model maps directly to the CLI skill pattern:

| CLI Concept | Cowork Equivalent |
|-------------|-------------------|
| `SKILL.md` | Plugin instruction file |
| MCP server (stdio) | MCP connector (declared in manifest) |
| `/research` command | Built-in web research capability |
| WorkIQ mock data | **Native WorkIQ access** (production M365 signals) |
| `node report-gen.cjs` | Plugin code action |

## Plugin Structure

```
cowork-plugin/
├── manifest.json          # Plugin metadata, MCP connectors, permissions
├── instructions/
│   └── sales-analysis.md  # Skill instructions (adapted from CLI SKILL.md)
└── actions/
    └── generate-report.js # Report generation action
```

### Example manifest.json

```json
{
  "name": "fabric-sales-agent",
  "displayName": "Fabric Sales Agent",
  "description": "Multi-source sales analysis powered by Fabric Data Agent",
  "version": "1.0.0",
  "mcpConnectors": [
    {
      "name": "wwi-sales-data",
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/workspaces/{workspace}/dataagents/{agent}/agent",
      "auth": "entra-delegated"
    }
  ],
  "permissions": [
    "workiq.read",
    "fabric.read",
    "web.search"
  ],
  "instructions": "instructions/sales-analysis.md"
}
```

## Why Cowork Matters

1. **Native WorkIQ** — Real M365 engagement signals (meetings, emails,
   files) without mocking or OBO complexity
2. **Enterprise distribution** — Deploy via M365 admin center, not
   per-user MCP config
3. **Managed runtime** — No infrastructure to maintain
4. **Same skill pattern** — Instructions written for CLI work in Cowork
   with minimal adaptation

## Prerequisites

- Microsoft 365 Frontier preview enrollment
- Cowork SDK access (currently limited preview)
- Entra ID app registration with Fabric delegated permissions

## Next Steps

When Frontier preview access is available:

1. Adapt `src/cli/skills/sales-analysis.md` to Cowork instruction format
2. Create MCP connector config for Fabric Data Agent
3. Package as M365 plugin
4. Test with native WorkIQ data (replacing mock)
