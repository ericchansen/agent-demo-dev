# Copilot CLI / VS Code — MCP Integration

This directory contains the **MCP server configuration** and **Copilot CLI
skills** that let you use the Fabric Sales Agent accelerator directly from
GitHub Copilot CLI or VS Code Copilot Chat.

## Prerequisites

| Requirement | Details |
|------------|---------|
| Python 3.11+ | Required for the local MCP servers |
| Project dependencies | `pip install -e ".[dev]"` from the repo root |
| Fabric Data Agent | Create a Data Agent in Microsoft Fabric and enable its MCP endpoint |
| Search provider (optional) | Set `SEARCH_PROVIDER` to `bing` or `tavily` and `SEARCH_API_KEY` for live web research. Defaults to `mock`. |
| SharePoint access (optional) | Set `SHAREPOINT_MODE=graph` and configure Azure Identity credentials for live SharePoint. Defaults to `mock`. |

## Installation

### 1. Install Python dependencies

```bash
cd /path/to/fabric-sales-agent-accelerator-scaffold
pip install -e ".[dev]"
```

### 2. Configure the Fabric Data Agent URL

Open `src/cli/mcp-config.json` and replace the placeholder in `wwi-sales-data`:

```json
"url": "<PASTE_YOUR_FABRIC_DATA_AGENT_MCP_URL_HERE>"
```

with the actual MCP endpoint URL from your Fabric Data Agent.

### 3. Merge MCP config into your editor / CLI

#### VS Code (workspace-level)

Copy the `mcpServers` block from `src/cli/mcp-config.json` into your
workspace's `.vscode/mcp.json`:

```jsonc
// .vscode/mcp.json
{
  "mcpServers": {
    // ... paste the three server entries here ...
  }
}
```

#### VS Code (user-level)

Open **Settings → Extensions → GitHub Copilot → MCP Servers** and add each
server entry.

#### GitHub Copilot CLI

Merge the entries into `~/.copilot/mcp-config.json`:

```jsonc
{
  "mcpServers": {
    // ... paste the three server entries here ...
  }
}
```

### 4. Set environment variables

```bash
# For live web research (optional — defaults to mock)
export SEARCH_PROVIDER=bing        # or tavily
export SEARCH_API_KEY=your-key

# For live SharePoint access (optional — defaults to mock)
export SHAREPOINT_MODE=graph
# Azure Identity must be configured (az login, managed identity, etc.)
```

## Skills

Skills are natural-language prompts that Copilot CLI recognizes. Place the
`.md` files from `src/cli/skills/` into your Copilot CLI skills directory
(typically `~/.copilot/skills/`) or reference them via your project config.

### Available skills

| Skill | File | Description |
|-------|------|-------------|
| **Generate Account Plan** | `account-plan.md` | Full workflow — pipeline + research + SharePoint → DOCX report |
| **Query Sales Pipeline** | `pipeline-query.md` | Ask natural-language questions about WWI sales data |
| **Research Customer** | `customer-research.md` | Web research on a customer — news, earnings, strategy |

### Example usage

```
Generate an account plan for Tailspin Toys
```

```
What are our top 10 customers by revenue?
```

```
Research Contoso Ltd — focus on earnings and expansion
```

## MCP Servers

| Server | Type | Description |
|--------|------|-------------|
| `wwi-sales-data` | HTTP | Fabric Data Agent — queries the WWI lakehouse |
| `researcher-agent` | stdio | Local Python process — web search for company intelligence |
| `sharepoint-agent` | stdio | Local Python process — SharePoint document retrieval |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `researcher-agent` fails to start | Ensure `pip install -e .` was run and `src/agents/researcher/mcp_server.py` exists |
| `sharepoint-agent` returns empty results | Check `SHAREPOINT_MODE` — set to `mock` for demo data |
| `wwi-sales-data` connection refused | Verify the Fabric Data Agent MCP URL and that the agent is running |
| MCP servers not visible in Copilot | Ensure `mcp-config.json` entries are merged into the correct config file |
