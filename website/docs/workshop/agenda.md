---
sidebar_position: 1
title: Two-Day Agenda
---

# Two-Day Workshop Agenda

This workshop is a hands-on path from a local Copilot CLI prototype to a production-oriented Azure AI Foundry agent for Microsoft 365 Copilot and Teams. Each block includes the outcome participants should be able to demonstrate before moving on.

## Day 1 — Build the working prototype

| Time | Module | Hands-on outcome |
|---|---|---|
| 09:00-09:30 | Orientation and architecture | Explain the two-surface model: Copilot CLI for fast iteration, Foundry for governed delivery. |
| 09:30-10:30 | Environment setup | Clone the repo, install Python and website dependencies, run `python scripts/predemo.py`, and confirm the local gates pass. |
| 10:30-11:30 | Deploy Azure resources | Deploy the dev Bicep template, understand the AI Services account and Foundry project, and confirm cost-safe defaults. |
| 11:30-12:00 | Choose your data platform | Decide whether the lab uses Microsoft Fabric Data Agent, Databricks Genie, or the deterministic WWI sample fallback. |
| 13:00-14:30 | Connect sales data | Configure Fabric MCP or Databricks Genie credentials, then run a natural-language Tailspin Toys query through the orchestrator. |
| 14:30-15:30 | CLI surface | Add MCP tools and skills to the Copilot CLI workflow, inspect tool responses, and compare Fabric vs Databricks behavior. |
| 15:30-16:30 | First report | Generate XLSX, HTML, PDF, and DOCX artifacts from quota data and review the evidence trail. |
| 16:30-17:00 | Day 1 checkpoint | Demonstrate a local quota report generated from the selected data platform or the WWI fallback. |

## Day 2 — Ship and operate the agent

| Time | Module | Hands-on outcome |
|---|---|---|
| 09:00-10:00 | Foundry agent registration | Create or verify the account-based Foundry project, register `SalesAgent`, and run `scripts/verify_foundry_agent.py`. |
| 10:00-11:00 | Foundry Playground | Open the agent in the portal, run the Tailspin Toys prompt, and inspect tool-call traces and generated artifact metadata. |
| 11:00-12:00 | Publish to Microsoft 365 | Use the current Foundry **Publish** flow to make the registered agent available in Microsoft 365 Copilot and Teams with the right Entra/RBAC assignments. |
| 13:00-14:00 | Customize for your data | Swap WWI sample assumptions for the participant's Fabric warehouse, Databricks Genie Space, or enterprise data contract. |
| 14:00-15:00 | Add reusable skills | Extend the quota workflow with one custom analysis or report-generation skill and add an offline test. |
| 15:00-16:00 | Hosted agent runtime | Build the hosted-agent container, probe `/healthz` and `/readyz`, and understand when bring-your-own-code hosting is preferable. |
| 16:00-16:45 | Evaluate and monitor | Run Foundry evals, review live-smoke readiness output, and map traces to new regression tests. |
| 16:45-17:00 | Graduation checkpoint | Present a credible path from local prototype to governed Foundry deployment, including cost and readiness guardrails. |

### Optional cloud-blocked lab

If Foundry portal access is unavailable, use [Foundry Local and DevUI](./foundry-local-devui) during the Day 2
evaluation block. It runs the deterministic planner -> data -> research -> work-context -> report pipeline, checks
Foundry Local installation status, and makes clear which proof still requires the live Foundry project.

## Facilitator checkpoints

Before each delivery, confirm:

| Check | Command or surface | Expected result |
|---|---|---|
| Offline readiness | `python scripts/predemo.py --docker` | Unit/eval/docs checks pass and the hosted container probes return HTTP 200. |
| Website | `cd website && npm run build` | Docusaurus builds without broken routes or anchors. |
| Links | `python scripts/validate_links.py --timeout 20 website/docs README.md` plus the Link Check workflow | Public links resolve and lychee validates fragments. |
| Live services | `.github/workflows/live-smoke.yml` | Configured backends run; unconfigured backends are reported as blocked, not silently treated as proof. |
