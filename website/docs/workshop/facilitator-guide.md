---
sidebar_position: 1
title: Facilitator Guide
---

# Facilitator Guide

This page is for people running this workshop with a group. It covers pacing, what to demo vs. hands-on, and how to adapt the material to different time slots.

## The two-day journey structure

The workshop follows a progressive narrative across two hands-on days. Each block has a demo outcome and a
participant artifact.

| Day | Block | Core concept | Participant artifact |
|---|---|---|---|
| Day 1 | Architecture and environment | Why agents need tools, MCP, auth, and real data. | Repo cloned, `uv sync --extra dev` complete. |
| Day 1 | Azure deploy | Bicep resources, public network access for dev, cost controls. | Resource group validated; Foundry project reachable. |
| Day 1 | Data platform | Choose Fabric Data Agent or Databricks Genie. | Golden sales query returns normalized rows. |
| Day 1 | CLI and first report | Copilot CLI / local Python invokes the quota pipeline. | XLSX, HTML, and PDF quota report. |
| Day 2 | Foundry agent | Project, agents, playground, tools, tracing. | Agent visible and testable in Foundry portal. |
| Day 2 | Publish and customize | M365 Copilot publishing, custom data, custom skills. | Workshop attendee knows the changes needed for their own data. |
| Day 2 | Hosted and multi-agent patterns | Single agent vs planner/data/research/context/report agents. | Multi-agent PoC run and architecture trade-off discussion. |
| Day 2 | Eval and monitor | Traces, failures, regression prompts, cost monitoring. | Evaluation checklist and troubleshooting path. |

**Total: 12-14 hours** across two days, including breaks, troubleshooting, and optional customization labs.

## Pacing options

### Half-day workshop (3 hours)
All six chapters. Chapters 1, 3, and 6 as demos/lectures. Chapters 2, 4, and 5 as guided hands-on.

### Full-day workshop (6 hours)
All chapters with deep hands-on. Add time for participants to build their own skills and experiment with different queries. Include the architecture section as a midday deep-dive.

### Two-day customer workshop (recommended)
Day 1 ends only after everyone has generated a local quota report. Day 2 starts in Foundry portal, then compares
single-agent and multi-agent patterns before publishing and monitoring.

### 90-minute overview
Chapters 1, 2, and 6 only. Focus on the narrative arc: why agents need data connections → show it working → show it deployed. Skip skills and tools — reference them as "what comes next."

### Multi-session series
One chapter per session (weekly or biweekly). Participants have homework between sessions to extend what they built.

## What to demo vs. hands-on

| Chapter | Recommendation |
|---|---|
| From Chat to Agent | **Lecture/demo** — set the narrative, show the problem |
| Ground It in Data | **Hands-on** — participants connect their own Data Agent |
| Give It Context | **Demo** (if mock data) or **Hands-on** (if real WorkIQ access) |
| Arm It with Tools | **Hands-on** — run the report generator, see real output |
| Build Reusable Skills | **Hands-on** — participants write their own skill |
| Ship It | **Demo** — show Foundry deployment, M365 chat |

## Golden prompts

Use these exact prompts to keep the room synchronized:

| Prompt | Expected proof |
|---|---|
| `What were Tailspin Toys' total sales last quarter?` | Data backend is connected. |
| `Generate a quota estimation report for Northwest territory` | XLSX/HTML/PDF pipeline works. |
| `Compare conservative vs aggressive scenarios for FY27` | Deterministic scenario controls work. |
| `What's our pipeline coverage ratio by salesperson?` | Tool routing beyond quota reports. |
| `Create a competitive analysis for Wingtip Toys` | Research + sales synthesis. |

## Visual checkpoints

Use the workshop visuals as stage gates instead of decoration:

| Checkpoint | Asset | What it proves |
|---|---|---|
| CLI report flow | `website/static/img/workshop/cli-report-flow.svg` plus `output/workshop-visual-proof.json` | Participants can run a prompt and produce report artifacts. |
| Generated artifacts | `website/static/img/workshop/quota-artifacts.svg` plus generated XLSX/HTML/PDF files | XLSX, HTML, and PDF outputs are concrete demo deliverables. |
| Foundry playground | `website/static/img/workshop/foundry-playground.svg` plus the manual portal checklist in `output/workshop-visual-proof.json` | The Foundry project, agent, Playground, and trace story are ready for Day 2 without fabricating authenticated screenshots. |

Generate the proof manifest before delivery:

```powershell
uv run python scripts/check_workshop_visuals.py
```

The manifest records the validated SVG assets, generated artifact paths and byte sizes, and the manual checklist for
capturing tenant-specific Foundry Playground screenshots.

## Live readiness checkpoints

Run these before participants arrive and record each as **passed** or **blocked with reason**:

| Check | Command | Pass condition |
|---|---|---|
| Foundry agent | `uv run python scripts/verify_foundry_agent.py` | `SalesAgent` is listed and the script prints `[OK] live registration + Playground response verified`. |
| Fabric live eval | `uv run python tests/eval/run_eval.py --pass-rate 80` | Golden-QA pass rate meets threshold, or the command blocks before question 1 because Fabric MCP env is missing. |
| Databricks Genie | `uv run python -m src.orchestrator "Use Databricks Genie to show sales by territory for Tailspin Toys"` | JSON includes `status: "ok"`, rows, `conversation_id`, and `message_id`, or `configuration_error` when the customer chose Fabric. |
| Publish prerequisites | `az provider show --namespace Microsoft.BotService --query registrationState -o tsv` | `Registered`; then verify published-agent RBAC and @mention visibility. |
| Live smoke workflow | `gh workflow run live-smoke.yml` | GitHub Actions shows passing jobs or clear blocked notices for unconfigured live services. |
| Public links | `gh workflow run link-check.yml` | The scheduled/manual Link Check workflow resolves public links and validates fragments. |

### Facilitator dev environment values

Keep tenant-specific values in your private shell profile, GitHub repository secrets, or a local `.env` file that is
not committed. Public workshop pages use placeholders so participants do not copy a demo tenant by accident.

```powershell
$env:AZURE_SUBSCRIPTION_ID="<your-subscription-id>"
$env:AZURE_RESOURCE_GROUP="<your-resource-group>"
$env:AI_SERVICES_ACCOUNT_NAME="<your-ai-services-account>"
$env:FOUNDRY_PROJECT_NAME="<your-foundry-project>"
$env:FOUNDRY_PROJECT_ENDPOINT="https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
$env:MODEL_DEPLOYMENT_NAME="gpt-4o"
```

Use the same values when setting GitHub Actions secrets for Live Smoke (`AZURE_SUBSCRIPTION_ID`,
`FOUNDRY_PROJECT_ENDPOINT`, and `MODEL_DEPLOYMENT_NAME`) and when running the Foundry portal verification scripts.

### Configure Live Smoke secrets

The workflow has two modes:

| Mode | Command | Use |
|---|---|---|
| Demo mode | `gh workflow run live-smoke.yml` | Best-effort live checks. Missing Foundry, Fabric, or Databricks config is reported as blocked and captured in `demo-readiness-report.json`. |
| Required mode | `gh workflow run live-smoke.yml -f require_live_backends=true` | Pre-customer gate. Missing live backend config fails the workflow instead of producing a green-but-skipped run. |

Set only the secrets for the live backends you plan to prove. Databricks Managed MCP is preferred for Genie smoke
coverage because Unity Catalog permissions are enforced by the platform-managed MCP server.

```powershell
gh secret set AZURE_CLIENT_ID
gh secret set AZURE_TENANT_ID
gh secret set AZURE_SUBSCRIPTION_ID
gh secret set FOUNDRY_PROJECT_ENDPOINT
gh secret set MODEL_DEPLOYMENT_NAME

# Fabric live eval: use a direct MCP endpoint, or workspace + Data Agent IDs.
gh secret set FABRIC_MCP_URL
gh secret set FABRIC_MCP_TOOL_NAME
gh secret set FABRIC_WORKSPACE_ID
gh secret set FABRIC_DATA_AGENT_ID

# Databricks Genie preferred path.
gh secret set DATABRICKS_GENIE_MCP_URL

# SDK-direct fallback when Managed MCP is unavailable.
gh secret set DATABRICKS_WORKSPACE_URL
gh secret set DATABRICKS_GENIE_SPACE_ID
gh secret set DATABRICKS_GENIE_WAREHOUSE_ID
gh secret set DATABRICKS_TOKEN
```

After each run, download the uploaded **demo-readiness-report** artifact. Treat `"status": "skipped"` for a live backend
as an explicit gap, not as evidence that the integration works.

## Prerequisites for participants

See [Setup Guide](./setup) for full details. At minimum:
- GitHub Copilot CLI installed and authenticated
- Python 3.11+ with the repo cloned and dependencies installed
- Access to one supported data platform: a Fabric Data Agent MCP endpoint or a Databricks Genie Space over Unity
  Catalog sales tables

## Tips

- **Start with the "why"** — Chapter 1 sets up the entire narrative. Don't skip it.
- **Use the demo script** — the [NCR Voyix QBR scenario](./demo-script) gives a concrete use case
- **Show the mermaid diagrams** — architecture visuals help non-technical audiences
- **Let people break things** — wrong queries, missing data, auth errors are all learning moments
- **End with "Ship It"** — showing M365 deployment makes the journey feel complete
- **Keep screenshots current** — when portal UI changes, update screenshots or use step-by-step text instead of stale images.
