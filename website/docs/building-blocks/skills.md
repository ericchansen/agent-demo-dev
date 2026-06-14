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

> 📖 [Copilot CLI skills overview](https://docs.github.com/copilot/github-copilot-in-the-cli/using-copilot-cli-skills) · [Creating custom skills](https://docs.github.com/copilot/github-copilot-in-the-cli/creating-custom-skills)

## Skills in this accelerator

| Skill | Purpose | Tools used |
|---|---|---|
| `quota-forecast` | QBR quota forecast for a customer | wwi-sales-data, workiq |
| (more coming) | | |

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

These demonstrate the progression from single-tool skills (one MCP call) to multi-source skills (parallel data + research + report generation).

## Skills vs Foundry agent prompts

In the CLI, skills are explicit workflow templates. In Foundry, the same logic lives in the agent's system prompt and tool instructions. When you translate a skill to Foundry:

- Skill parameters → Foundry tool input schemas
- Skill steps → Agent system prompt instructions
- Skill output format → Response formatting instructions

> 📖 [Foundry agent instructions](https://learn.microsoft.com/azure/ai-foundry/how-to/agents/agents-create#configure-agent-instructions)

## Further reading

- [Copilot CLI skills](https://docs.github.com/copilot/github-copilot-in-the-cli/using-copilot-cli-skills)
- [Skill authoring guide](https://docs.github.com/copilot/github-copilot-in-the-cli/creating-custom-skills)
- [Prompt engineering best practices](https://learn.microsoft.com/azure/ai-services/openai/concepts/prompt-engineering)
