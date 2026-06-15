---
sidebar_position: 3
title: Demo Script
---

# Demo Script — QBR Prep Scenario

## The scene

You're an Account Executive at Wide World Importers preparing for a Quarterly Business Review with Tailspin Toys. You need a quota forecast brief — sales data, engagement context, and a formatted report.

This demo shows the same workflow in two surfaces.

![Copilot CLI report flow](/img/workshop/cli-report-flow.svg)

## Act 1 — CLI (Developer Audience)

> "Let's start where every agent begins — prototyping in the CLI."

### Query 1: Sales data

```
@wwi-sales-data What were Tailspin Toys' total sales by product category for the last 12 months?
```

*Expected: The agent queries the Fabric Data Agent → returns a sales breakdown table*

**What to point out:**
- The agent didn't write SQL — the Data Agent handled NL→SQL
- The MCP server was auto-discovered from `.github/mcp.json`
- No custom orchestration code — Copilot CLI handled tool selection

### Query 2: Quota forecast

```
Based on that data, generate a quota forecast for Tailspin Toys for FY27
```

*Expected: The agent calls the forecast skill -> produces XLSX, HTML, and PDF report artifacts with projections*

**What to point out:**
- The skill chained multiple tool calls automatically
- Output includes projections based on historical trends
- This is a reusable workflow, not a one-off prompt

### Query 3: Scenario comparison

```
Now give me an aggressive and a conservative version of that quota
```

*Expected: The agent re-runs the skill with `scenario: aggressive` and `scenario: conservative` -> two artifact sets whose totals bracket the base case*

**What to point out:**
- Scenarios are deterministic, not model guesses
- The Excel workbook includes an Assumptions sheet for auditability
- HTML artifacts embed the chart inline for easy sharing

![Generated quota artifacts](/img/workshop/quota-artifacts.svg)

> "That's the prototype. Same MCP servers, zero custom code. Now let's see the business user experience."

## Act 2 — M365 Copilot (Business User Audience)

> "Same agent, now published to M365 via Azure AI Foundry."

### Query 1: Customer brief

```
@WWISalesAgent Brief me on Tailspin Toys — what's our recent engagement and sales activity?
```

*Expected: Agent pulls Fabric sales data + WorkIQ activity data → combined summary*

**What to point out:**
- Both data sources (Fabric + WorkIQ) were called automatically
- The response includes *your* engagement, not just company data
- This runs through Entra auth — enterprise-grade identity

### Query 2: Forecast report

```
@WWISalesAgent Generate an FY27 quota forecast report for Tailspin Toys
```

*Expected: Agent queries Fabric, adds WorkIQ context, generates XLSX/HTML/PDF artifacts -> returns file paths or sharing links*

**What to point out:**
- The agent produced real artifacts, not just chat text
- The same scenario-aware quota estimator runs behind the Foundry function tool
- Same Data Agent backend as the CLI, different output format

## Transition narrative

Between Act 1 and Act 2, explain the translation:

> "The CLI used MCP servers. Foundry uses platform tools. Same HTTP endpoints underneath. The CLI skill became the agent's system prompt. Interactive OAuth became OBO. Markdown output became a DOCX with OneDrive upload. The backend didn't change — the surface did."

## Fallback table

| Failure | Recovery |
|---|---|
| Cross-tenant OAuth prompt | Pre-auth all surfaces 10 min before demo |
| WorkIQ not responding | Show pre-cached activity summary |
| Agent not visible in M365 | Use Foundry playground instead |
| Artifact upload fails | Show pre-generated XLSX/HTML/PDF files from local run |
| Fabric capacity paused | Resume 15 min before: `az fabric capacity resume` |
| Slow first query | Warm up with a test query 5 min before demo |

## Pre-demo checklist

- [ ] Fabric capacity is running (`az fabric capacity show`)
- [ ] Test a query against the Data Agent
- [ ] Copilot CLI authenticated and MCP servers loaded
- [ ] Foundry agent responding in playground
- [ ] M365 Copilot can see the agent (@mention works)
- [ ] Pre-generated XLSX/HTML/PDF artifacts available as fallback
