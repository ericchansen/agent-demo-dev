---
sidebar_position: 1
title: From Chat to Agent
---

# From Chat to Agent

Most people's first experience with AI is a chatbot — you ask it something, it gives you an answer. That's useful, but it's limited. The answer comes from the model's training data and whatever you typed into the prompt. It doesn't know your customers. It doesn't know what you worked on last week. It can't generate a report and put it in your OneDrive.

This workshop is about closing that gap. You'll build an AI agent that works more like a coworker than a search engine — one that connects to your actual business data, understands your recent activity, and produces real deliverables.

## What makes an agent different from a chatbot?

A chatbot answers questions. An agent does work. The difference comes down to what the agent can *reach*:

| Capability | Chatbot | Agent |
|---|---|---|
| Answer general knowledge questions | ✅ | ✅ |
| Query your company's sales data | ❌ | ✅ via [Fabric Data Agent](../building-blocks/fabric-data-agent) |
| Know what meetings you had this week | ❌ | ✅ via [WorkIQ](../building-blocks/workiq) |
| Generate a formatted report | ❌ | ✅ via [report tools](../building-blocks/report-generation) |
| Upload output to OneDrive | ❌ | ✅ via [tool integration](../building-blocks/mcp) |
| Remember and reuse workflows | ❌ | ✅ via [skills](../building-blocks/skills) |

Each row in that table is a connection you'll make during this workshop.

## The journey

This workshop follows the progression of building a working agent, layer by layer:

1. **[Ground It in Data](./ground-it-in-data)** — Connect to a Fabric Lakehouse through the Data Agent. Your agent can now answer questions about real business data using natural language.

2. **[Give It Context](./give-it-context)** — Connect to WorkIQ for M365 activity signals. The agent now knows who you've emailed, what meetings you've had, and what you've been working on. Its answers become personalized.

3. **[Arm It with Tools](./arm-it-with-tools)** — Connect tools that produce real output — reports, forecasts, documents. The agent doesn't just tell you things, it creates deliverables.

4. **[Build Reusable Skills](./build-reusable-skills)** — Compose data, context, and tools into repeatable workflows. Skills are shareable, versionable, and composable.

5. **[Ship It](./ship-it)** — Choose how users interact with the agent. The [CLI surface](../architecture/cli-surface) is great for developers. [Foundry → M365](../architecture/foundry-surface) reaches business users in Teams and Copilot Chat. Same backend, different reach.

## The scenario

Throughout this workshop, you'll work with the [Wide World Importers](../building-blocks/wwi-dataset) sample dataset — a wholesale novelty goods company. You'll play the role of an account executive preparing for a quarterly business review with a customer. By the end, your agent will be able to:

- Answer "What were Tailspin Toys' sales by category last quarter?" by querying the Lakehouse
- Surface recent email and meeting activity with that customer
- Generate a formatted FY forecast report with charts and citations
- Deliver that report as a downloadable DOCX through OneDrive

None of that requires the agent to be "smart." It requires the agent to be *connected*.

## Prerequisites

Before starting, you'll need:
- A [Microsoft Fabric](https://learn.microsoft.com/fabric/get-started/fabric-trial) workspace with the WWI sample data loaded
- [GitHub Copilot CLI](https://docs.github.com/copilot/github-copilot-in-the-cli) installed
- Python 3.11+ (we recommend [uv](https://docs.astral.sh/uv/) for environment management)

See the [Setup Guide](../workshop/setup) for detailed environment configuration.
