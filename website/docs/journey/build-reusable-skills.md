---
sidebar_position: 5
title: Build Reusable Skills
---

# Build Reusable Skills

By now your agent can query data, pull activity context, and generate reports. But each time, you're explaining the full workflow from scratch: "Get Tailspin Toys' sales, check my recent engagement, then generate a forecast report." That's fine for ad-hoc questions, but for workflows you repeat — customer briefs, QBR prep, pipeline reviews — you want a shortcut.

That's what skills are for. A skill is a reusable prompt template that encapsulates a multi-step workflow. Instead of explaining the steps every time, you invoke the skill and it handles the orchestration.

## What is a skill?

A skill is a structured prompt that:
- **Describes an intent** — what the user is trying to accomplish
- **Chains tool calls** — specifies which tools to call and in what order
- **Formats output** — defines how results should be presented
- **Accepts parameters** — customer name, time range, report type, etc.

Skills are the "glue" between raw tool capabilities and repeatable business workflows.

> 📖 **Learn more:** [Copilot CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) · [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)

## Example: quota-forecast skill

The `quota-forecast` skill in this accelerator encapsulates the QBR prep workflow:

```yaml
# src/cli/skills/quota-forecast.yaml
name: quota-forecast
description: Generate a quarterly business review forecast for a customer
parameters:
  - name: customer
    description: Customer name (e.g., "Tailspin Toys")
    required: true
  - name: fiscal_year
    description: Target fiscal year (e.g., "FY27")
    required: true
steps:
  - tool: sales-data
    prompt: "Get {customer}'s sales by category for the last 4 quarters"
  - tool: workiq
    prompt: "Summarize my recent engagement with {customer}"
  - format: |
      ## {customer} — {fiscal_year} Forecast
      ### Sales Trends
      {sales_data}
      ### Recent Engagement
      {activity_summary}
      ### Forecast
      Based on the trends above, project {fiscal_year} by category.
```

### Using the skill

```
copilot
> /quota-forecast customer="Tailspin Toys" fiscal_year="FY27"
```

Or just describe what you want — Copilot CLI matches your intent to available skills:

```
copilot
> Prepare a QBR forecast for Tailspin Toys
```

The skill handles the rest: query the data, pull the context, format the output.

## Skills vs. tools vs. agents

These terms get confused often. Here's how they relate in this architecture:

| Concept | What it is | Example |
|---|---|---|
| **Tool** | A single capability the agent can call | `sales-data` (query Lakehouse) |
| **Skill** | A workflow template that chains tools | `quota-forecast` (data + context + format) |
| **Agent** | The orchestrator that selects tools/skills based on intent | Copilot CLI, Foundry Agent |

Tools are atomic. Skills are composed. Agents decide what to use.

## Sharing skills

Skills are files in your repository. This means they're:
- **Versionable** — tracked in git, reviewed in PRs
- **Shareable** — anyone who clones the repo gets your skills
- **Composable** — one skill can reference others
- **Portable** — skills written for CLI can inform Foundry agent prompts

In the `.github/` directory or `src/cli/skills/`, skills are auto-discovered by Copilot CLI when you work in the project.

## Building your own

The pattern for creating a new skill:

1. **Identify the workflow** — what do you do repeatedly that involves multiple tool calls?
2. **Define the parameters** — what varies each time? (customer name, date range, etc.)
3. **Sequence the tools** — what data needs to be gathered, in what order?
4. **Design the output** — how should results be formatted and presented?
5. **Test it** — run the skill with different inputs, check the output quality

### Ideas for skills

- **Pipeline review** — pull all open opportunities, recent activity per account, flag risks
- **Meeting prep** — customer brief + recent emails + last meeting notes
- **Territory summary** — aggregate sales across all accounts in a region
- **Win/loss analysis** — compare closed-won vs. closed-lost deals by category

Each of these follows the same pattern: gather data from Fabric, enrich with WorkIQ context, format into a useful deliverable.

## What you've accomplished

You've gone from raw tool connections to repeatable, shareable workflows. Your agent isn't just capable — it's efficient. But so far you've been working in the CLI, which is great for development but doesn't reach business users. In the final chapter, you'll learn how to ship this same agent to M365 Copilot and Teams.

**Next: [Ship It →](./ship-it)**
