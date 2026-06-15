---
sidebar_position: 7
title: Enable Live Smoke
---

# Enable Live Smoke

The **Live Smoke** workflow (`.github/workflows/live-smoke.yml`) is the pre-customer readiness check. It runs
five jobs: Foundry registration, Fabric golden-QA eval, Databricks Genie query, the published-site check, and
the offline demo-readiness gate. The three live-backend jobs only execute when their secrets are present, and
they only **fail the run** when you mark that backend as required.

This page turns the recurring "required mode is red" blocker into a few facilitator commands.

:::info Who needs this
Only the facilitator preparing a live demo needs Live Smoke green. Participants following the workshop do not
need it — the offline gate (`demo-readiness`) runs on every push with no secrets.
:::

## 1. Wire GitHub OIDC → Azure in one command

`azure/login@v3` authenticates with a **federated credential** (GitHub OIDC), so no client secret is stored in
the repo. Create the app, federated credential, role assignment, and `AZURE_*` secrets with the setup script:

```powershell
# Preview every change without touching anything
./scripts/setup_oidc.ps1 -DryRun

# Apply
./scripts/setup_oidc.ps1 -SubscriptionId $env:AZURE_SUBSCRIPTION_ID
```

```bash
scripts/setup_oidc.sh --dry-run
scripts/setup_oidc.sh --subscription-id "$AZURE_SUBSCRIPTION_ID"
```

The script:

- is **idempotent** — re-running reuses the existing app, federated credential, role assignment, and secrets;
- pins the OIDC subject to `repo:ericchansen/agent-demo-dev:ref:refs/heads/main`;
- sets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` as repo secrets;
- on a Microsoft Graph failure (interactive CAE challenge, or missing Entra role) prints the exact
  federated-credential JSON and the `az ad app federated-credential create` command so someone with
  **Application Administrator** or app ownership can finish by hand.

### Permissions the runner of the script needs

| Action | Required permission |
|---|---|
| Create the app + federated credential | Entra **Application Administrator** (or ownership of an existing app passed via `-AppId`) |
| Assign Contributor on the resource group | **Owner** or **User Access Administrator** on the workshop resource group (`AZURE_RESOURCE_GROUP`) |
| Set GitHub secrets | **Admin** on the repository (`gh auth status` must show this) |

## 2. Add the backend secrets you will demo

Set only the platform you teach. Each block lists exactly what the matching Live Smoke job checks.

### Foundry (agent registration)

```powershell
gh secret set FOUNDRY_PROJECT_ENDPOINT   # https://<account>.services.ai.azure.com/api/projects/<project>
gh secret set MODEL_DEPLOYMENT_NAME      # e.g. gpt-4o
```

`AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` come from step 1.

### Fabric (golden-QA live eval)

```powershell
gh secret set FABRIC_MCP_URL             # or FABRIC_WORKSPACE_ID + FABRIC_DATA_AGENT_ID
gh secret set FABRIC_MCP_TOOL_NAME
```

### Databricks Genie

```powershell
gh secret set DATABRICKS_GENIE_MCP_URL   # managed MCP transport
# or SDK-direct:
gh secret set DATABRICKS_WORKSPACE_URL
gh secret set DATABRICKS_GENIE_SPACE_ID
gh secret set DATABRICKS_TOKEN
```

## 3. Run required mode for only your platform

Historically `require_live_backends=true` demanded all three backends, so a Fabric-only setup still failed on
Databricks. Use the per-backend inputs to require **only** the platform your workshop uses:

```powershell
gh workflow run "Live Smoke" -f require_foundry=true
gh workflow run "Live Smoke" -f require_fabric=true
gh workflow run "Live Smoke" -f require_databricks=true
gh run watch
```

| Input | Effect |
|---|---|
| `require_live_backends=true` | Require all three live backends (original behavior). |
| `require_foundry=true` | Fail only if the Foundry job is skipped/failed. |
| `require_fabric=true` | Fail only if the Fabric job is skipped/failed. |
| `require_databricks=true` | Fail only if the Databricks job is skipped/failed. |

You can combine flags (for example `-f require_foundry=true -f require_fabric=true`). With no flags the run is
**demo mode**: live backends are best-effort and a skip never fails the workflow.

## 4. Read the result

Every run uploads `demo-readiness-report.json` and writes a Step Summary table. Each live-backend row shows:

- `status`: `ran` (secrets present, live path executed), `skipped` (secrets absent), or `failed` (ran and
  failed);
- `required`: whether this run treated that backend as a gate;
- `required_backends`: the per-platform requirement the run used.

The run fails only when a `required` backend is `failed` or `skipped`, or when an always-on check
(published-site, offline readiness) fails.

:::warning Out of scope for an autonomous agent
Creating the federated credential mutates Microsoft Graph and may trigger an interactive Conditional Access /
CAE challenge that a headless agent cannot satisfy. In that case the setup script prints the manual command —
a facilitator runs it once, and subsequent runs are green.
:::

See the [Troubleshooting](troubleshooting#oidc-and-live-smoke) page for specific OIDC and required-mode errors.
