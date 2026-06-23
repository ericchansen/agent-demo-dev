---
sidebar_position: 5
title: Skills & Prompt Templates
---

# Skills & Prompt Templates

A skill is a reusable workflow template that chains tool calls and formats output. Skills are the layer between raw tool capabilities ("query Lakehouse") and business workflows ("prepare a QBR forecast for Tailspin Toys").

## Anatomy of a skill

A skill defines:
- **Name and description** — how the agent discovers and selects it
- **Parameters** — what varies each time (customer name, date range, etc.)
- **Steps** — which tools to call and in what order
- **Output format** — how results are presented to the user

Skills live as files in your repository (`src/cli/skills/` or `.github/copilot/skills/`) and are auto-discovered by Copilot CLI.

> 📖 [Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) · [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)

## Skills in this accelerator

| Skill | Purpose | Tools used |
|---|---|---|
| `quota-forecast` | QBR quota forecast for a customer | sales-data, workiq |
| `sales-analysis` | Multi-source customer analysis with Excel output | sales data, research, report generator |
| `competitive-intel` | Customer and market research brief | web research, market data |

## Writing a skill

### 1. Define the intent
What business question does this skill answer? Be specific — a well-scoped skill is more reliable than a broad one.

### 2. Chain the tools
What data does the skill need? Map each data requirement to a tool call.

### 3. Format the output
How should results look? Use markdown templates with placeholders for tool outputs.

### 4. Test with variations
Try different customer names, date ranges, and edge cases. Skills should degrade gracefully when data is missing.

## Skills in this accelerator

The `src/cli/skills/` directory contains several production-quality skills:

| Skill | What it does | Tools used |
|---|---|---|
| `sales-analysis.md` | Deep multi-source customer analysis with Excel output | Fabric (WWI), web research, report generator |
| `company-financials.md` | SEC EDGAR financial data lookup | Fabric (Market Data) |
| `competitive-intel.md` | Market intelligence gathering | Fabric (Market Data), web research |
| `market-overview.md` | Industry and market summary | Web research |
| `quota-forecast.md` | Quota attainment forecast | Fabric (WWI) |
| `quota-methodology/SKILL.md` | **Versioned** quota-estimation methodology (formula + bounds) | Fabric/Databricks, research, WorkIQ, quota estimator |

These demonstrate the progression from single-tool skills (one MCP call) to multi-source skills (parallel data + research + report generation).

## Versioned skills: the Foundry Toolbox pattern

A skill like [`quota-forecast.md`](https://github.com/ericchansen/agent-demo-dev/blob/main/src/cli/skills/quota-forecast.md) tells the agent *which tools to call*. But the **business logic** — the exact growth-rate formula, the clamp bounds, the scenario adjustments — is what must stay identical whether a quota is computed in the CLI, a Foundry agent, or a Databricks Supervisor function. That contract lives in a **versioned `SKILL.md`**:

[`src/cli/skills/quota-methodology/SKILL.md`](https://github.com/ericchansen/agent-demo-dev/blob/main/src/cli/skills/quota-methodology/SKILL.md)

It carries `version`, `last_reviewed`, an explicit `tools` list, and the full deterministic methodology extracted from `src/agents/quota_estimator/pipeline.py`. A unit test (`tests/unit/test_quota_methodology_skill.py`) asserts the documented scenario adjustments and formula constants match the implementation, so the artifact cannot silently drift. Bump `version` whenever the formula changes.

> 💡 This is the "Foundry Toolbox" idea: treat the methodology as a governed, versioned artifact you import into any surface, not prose you re-explain each time.

## Translating a CLI skill to Foundry tool instructions

In the CLI, a skill is an explicit workflow template. In Azure AI Foundry, the same logic is split across the agent definition. Map it like this:

| CLI skill element | Foundry equivalent | Where it goes |
|---|---|---|
| `name` / `description` front matter | Agent name + description | Agent definition |
| Methodology / steps body | System prompt (instructions) | Agent `instructions` |
| `tools` list | Tool / connection wiring | `FunctionTool`, MCP tool, or a Databricks Supervisor `uc_function` |
| Parameters | Tool input JSON schema | Tool definition `parameters` |
| Output contract | Response-formatting instructions | Agent `instructions` |

Concretely, for the quota methodology:

1. **Instructions** — paste the `## Methodology (the formula)` and `## Output contract` sections into the agent's system prompt verbatim. The formula constants are the contract; do not paraphrase them.
2. **Tools** — register `generate_quota_estimation_report` as a Foundry `FunctionTool` (or the hosted-agent tool), and wire the data backend through a Foundry **connection** (Fabric/Databricks connections are preview, created via code/Bicep and referenced by name).
3. **Versioning** — keep the `version` from `SKILL.md` in the agent description (e.g. `quota-methodology v1.0.0`) so you can tell which methodology a deployed agent encodes.

The same `SKILL.md` also maps onto the [Databricks Supervisor](databricks-supervisor) path: the methodology becomes a Unity Catalog `uc_function`, and the `tools` list becomes Supervisor tool specs.

## Skills vs Foundry agent prompts

In the CLI, skills are explicit workflow templates. In Foundry, the same logic lives in the agent's system prompt and tool instructions. When you translate a skill to Foundry:

- Skill parameters → Foundry tool input schemas
- Skill steps → Agent system prompt instructions
- Skill output format → Response formatting instructions

> 📖 [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview)

## Further reading

- [Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [Prompt engineering best practices](https://learn.microsoft.com/azure/ai-services/openai/concepts/prompt-engineering)
