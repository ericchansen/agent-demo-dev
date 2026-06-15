---
sidebar_position: 6
title: Troubleshooting
---

# Troubleshooting

Use this page when something in the workshop does not behave as the guide describes. It is organized by
the part of the stack that fails: **Foundry**, **OIDC / Live Smoke**, **Fabric**, **Databricks Genie**,
**Microsoft 365 publishing**, **hosted agent**, and the **website build**. Each entry lists the symptom, the
most common cause, and the exact command or setting that fixes it.

:::tip Read the error category first
Most failures print a category in the error text — `azure/login`, `ConfigurationError`, `MCP`, `RBAC`,
`Docusaurus`. Jump to the matching section below rather than reading top to bottom.
:::

## Foundry agent

### `ConfigurationError: FOUNDRY_PROJECT_ENDPOINT is not set`

The SDK path in `src/orchestrator/foundry_agent.py` and `scripts/verify_foundry_agent.py` needs an
**account-based** Foundry project endpoint, not the hub workspace.

- **Wrong:** an `azureml://…` hub workspace id, or the hub name `fabric-agent-hub-dev`.
- **Right:** `https://<account>.services.ai.azure.com/api/projects/<project>`.

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://fabricagentaidev2026.services.ai.azure.com/api/projects/fsa-foundry-project-dev
MODEL_DEPLOYMENT_NAME=gpt-4o
```

See [Foundry Surface → Project and portal experience](../architecture/foundry-surface#project-and-portal-experience)
for why the hub-based `fsa-project-dev` and the account-based `fsa-foundry-project-dev` are different
resources.

### The agent is not visible in the Foundry portal

Agents are **not** created by the infrastructure deploy. They are registered by the SDK. Run the registration
once, then refresh the portal:

```powershell
uv run python scripts/verify_foundry_agent.py
```

A successful run prints `[OK] live registration + Playground response verified`. If the project Agents list is
still empty afterward, you are pointed at a different project than the portal tab — re-check
`FOUNDRY_PROJECT_ENDPOINT`.

### `(no response text returned)` from a query

The model deployment named in `MODEL_DEPLOYMENT_NAME` does not exist on the project. List deployments and
match the name exactly:

```powershell
az cognitiveservices account deployment list -g rg-fabric-agent-dev -n fabricagentaidev2026 -o table
```

## OIDC and Live Smoke

### `azure/login` fails with `AADSTS70021: No matching federated identity record found`

The GitHub Actions OIDC subject does not match any federated credential on the app. The subject must be
exactly `repo:ericchansen/agent-demo-dev:ref:refs/heads/main`. Fix it in one command:

```powershell
./scripts/setup_oidc.ps1            # or: scripts/setup_oidc.sh
```

```bash
./scripts/setup_oidc.sh --dry-run   # preview every change first
```

The script is idempotent and prints the exact `az ad app federated-credential create` command plus the
credential JSON if it cannot reach Microsoft Graph (for example, an interactive Conditional Access / CAE
challenge or a missing Entra role). Hand that output to someone with **Application Administrator** or app
ownership to finish.

### Required-mode Live Smoke fails even though my platform works

`require_live_backends=true` requires **all three** live backends (Foundry, Fabric, Databricks). If your
workshop only uses one platform, require just that one:

```powershell
gh workflow run "Live Smoke" -f require_foundry=true
gh workflow run "Live Smoke" -f require_fabric=true
gh workflow run "Live Smoke" -f require_databricks=true
```

A `skipped` live-backend check only fails the run when that backend is **required**. The job summary table and
`demo-readiness-report.json` show which backends were required, ran, or were skipped. Full setup is on the
[Enable Live Smoke](enable-live-smoke) page.

### Local Azure reads hit an interactive CAE / Conditional Access prompt

A headless agent cannot complete an interactive token challenge. Run `az login` in an interactive terminal
first, or perform the Graph mutation from a workstation that satisfies Conditional Access, then re-run the
setup script — it reuses what already exists.

## Fabric

### Fabric Data Agent MCP returns no rows or times out

1. Confirm the workspace and agent ids, or the MCP URL:

   ```dotenv
   FABRIC_MCP_URL=https://<host>/mcp
   FABRIC_MCP_TOOL_NAME=<tool name>
   # or
   FABRIC_WORKSPACE_ID=<workspace guid>
   FABRIC_DATA_AGENT_ID=<data agent guid>
   ```

2. The signed-in identity needs at least **Viewer** on the Fabric workspace and access to the lakehouse the
   Data Agent reads. See [Fabric Data Agent](../building-blocks/fabric-data-agent).
3. Network errors (`ConnectionError`, TLS resets) usually mean the Fabric capacity has **public network
   access** disabled. For the workshop, dev resources deploy with public access enabled
   (`publicNetworkAccess = 'Enabled'` in `infra/parameters/dev.bicepparam`).

### The demo runs but uses fallback data

When `FABRIC_IQ_CONNECTION_ID` is unset the agent intentionally registers a local, demo-safe `fabric_query`
tool so registration and the Playground work before live data is wired. This is expected on day one. Set the
connection id to query live Fabric.

## Databricks Genie

### `DATABRICKS_GENIE_*` not configured

Two transports are supported — pick one:

```dotenv
# Managed MCP (preferred)
DATABRICKS_GENIE_MCP_URL=https://<workspace>/api/2.0/mcp/genie/<space-id>

# SDK-direct
DATABRICKS_WORKSPACE_URL=https://<workspace>.azuredatabricks.net
DATABRICKS_GENIE_SPACE_ID=<genie space id>
DATABRICKS_TOKEN=<pat or leave unset to use other auth>
```

### `PERMISSION_DENIED` from Unity Catalog or the Genie space

The principal needs `CAN RUN` on the Genie space and `SELECT` on the underlying Unity Catalog tables, plus
`USE CATALOG` / `USE SCHEMA`. Grant them in the Databricks UI or with SQL, then retry. See
[Databricks Genie](../building-blocks/databricks-genie).

## Microsoft 365 publishing

### Publish to Copilot is greyed out or fails with an authorization error

- The publishing user needs the right Microsoft 365 role (typically **Teams administrator** or delegated app
  management) and the tenant must allow custom agents.
- A prompt agent registered by `verify_foundry_agent.py` has `identity=None` and **cannot** be published
  directly. The production M365/Teams path is the **hosted agent** (`WWISalesHostedAgent`), which receives a
  dedicated Entra agent identity when deployed. See [Deploy the Hosted Agent](hosted-agent-deploy).
- Reference: [Publish agents to Microsoft 365 Copilot and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot).

## Hosted agent

### Container builds but `/readyz` never turns ready

`/readyz` reports the adapter selection and never raises. If it reports `adapter unavailable`, the model
environment variables are missing. Set `MODEL_ENDPOINT` / `MODEL_DEPLOYMENT` (or run with the local runtime
adapter, which is always available). Full build/deploy/test steps are on
[Deploy the Hosted Agent](hosted-agent-deploy).

### `POST /responses` returns `415 unsupported_media_type`

Send `Content-Type: application/json`. The Responses route also rejects `stream=true` with
`400 streaming_not_supported` — the hosted server returns non-streaming Responses payloads only.

## Website build and links

### `npm run build` fails or warns

Docusaurus is configured to treat broken links as errors. Run the build from the `website/` directory:

```powershell
cd website
npm install
npm run build
```

A broken **internal** link prints the source page and the missing target — fix the relative path. The build
must finish with `[SUCCESS] Generated static files in "build"` and **zero** warnings.

### External link check fails

Validate every external link the same way CI does:

```powershell
python scripts/validate_links.py --timeout 20 website/docs README.md
```

If a Microsoft Docs URL 404s, find the current location with research and update the link — do not leave a
broken URL, it undermines the workshop's credibility.

## Still stuck?

- Re-run the offline readiness gate: `python scripts/demo_check.py`.
- Re-run the full unit suite: `pytest tests/unit/`.
- Check recent CI: `gh run list --limit 5`.
- Capture the exact command, the full error text, and which platform you chose before asking a facilitator.
