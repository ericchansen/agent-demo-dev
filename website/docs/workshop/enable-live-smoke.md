---
sidebar_position: 7
title: Enable Live Smoke
---

# Enable Live Smoke

The **Live Smoke** workflow (`.github/workflows/live-smoke.yml`) is the pre-customer readiness check. It runs
six jobs: Foundry registration, Fabric golden-QA eval, Databricks Genie query, the published-site check, the
offline demo-readiness gate, and the recorded/offline backend E2E proof. The three live-backend jobs only
execute when their secrets are present, and they only **fail the run** when you mark that backend as required.

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

**Auth mode (independent of the endpoint secrets above):**

| Mode | Secrets | When the job uses it |
|---|---|---|
| Service principal (recommended for CI) | `FABRIC_CLIENT_ID` + `FABRIC_CLIENT_SECRET` + `FABRIC_TENANT_ID` | All three are set — the client authenticates with `ClientSecretCredential`. |
| OIDC federated identity | _none of the three_ | None are set — the client falls back to `DefaultAzureCredential` using the `azure/login` OIDC identity from step 1. |

```powershell
# Headless service-principal auth — register an Entra app, grant it access to the
# Fabric Data Agent, then set all three secrets together:
gh secret set FABRIC_CLIENT_ID
gh secret set FABRIC_CLIENT_SECRET
gh secret set FABRIC_TENANT_ID
```

> ⚠️ Set **all three** Fabric SPN secrets or **none**. A partial triple is treated as a misconfiguration: the
> Fabric job (and `python tests/eval/run_eval.py`) blocks with an explicit "Fabric SPN auth is partial" message
> instead of silently downgrading to the OIDC identity. The Fabric job's config step prints which auth mode it
> selected, and `scripts/demo_check.py` shows the same auth mode in its **Live backend readiness** matrix.

### Databricks Genie

```powershell
gh secret set DATABRICKS_GENIE_MCP_URL   # managed MCP transport
gh secret set DATABRICKS_HOST            # https://adb-<workspace-id>.<region>.azuredatabricks.net
gh secret set DATABRICKS_CLIENT_ID       # OAuth M2M service principal
gh secret set DATABRICKS_CLIENT_SECRET   # OAuth M2M service principal secret
# or SDK-direct:
gh secret set DATABRICKS_WORKSPACE_URL
gh secret set DATABRICKS_GENIE_SPACE_ID
gh secret set DATABRICKS_TOKEN           # PAT alternative to OAuth M2M
```

For unattended CI, prefer OAuth machine-to-machine (`DATABRICKS_CLIENT_ID` +
`DATABRICKS_CLIENT_SECRET`) over a user PAT. The Live Smoke job maps those secrets
into the Databricks SDK unified auth chain for both the managed MCP and SDK-direct
transports.

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
(published-site, offline readiness, recorded/offline backend E2E proof) fails.

## 5. Backend Validation Status

A **green** Live Smoke run does not always mean every backend was exercised. In **demo mode** an unconfigured
backend reports `skipped` and the workflow still passes — green because skipped, **not** because the live path
was proven. Use this matrix to read the honest state of each backend and know exactly what it takes to move a
row from `skipped` to live-proven (`ran`).

| Backend | Default CI status | What "ran" proves | Secrets required to prove it live | How a facilitator proves it |
|---|---|---|---|---|
| **Foundry** (agent registration) | `skipped` until secrets set; **provable headlessly** | The account-based project registers `WWISalesAgent` and answers a Playground Responses query. | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `FOUNDRY_PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME` | `uv run python scripts/verify_foundry_agent.py` → `[OK] live registration + Playground response verified`, then `-f require_foundry=true`. |
| **Fabric** (golden-QA eval) | `skipped` until secrets set | The Fabric Data Agent MCP answers the golden-QA questions over live lakehouse data. | `FABRIC_MCP_URL` (or `FABRIC_WORKSPACE_ID` + `FABRIC_DATA_AGENT_ID`), `FABRIC_MCP_TOOL_NAME`, plus an auth mode — either `FABRIC_CLIENT_ID` + `FABRIC_CLIENT_SECRET` + `FABRIC_TENANT_ID` (service principal) or the `AZURE_*` OIDC identity (DefaultAzureCredential). | Provision a Fabric Data Agent, set the endpoint + auth secrets, run `-f require_fabric=true`. |
| **Databricks** (Genie query) | `skipped` until secrets set | A Genie space answers a query over Unity Catalog tables. | `DATABRICKS_GENIE_MCP_URL` + `DATABRICKS_HOST` + OAuth M2M (`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`) for managed MCP; or `DATABRICKS_WORKSPACE_URL` + `DATABRICKS_GENIE_SPACE_ID` + either OAuth M2M or `DATABRICKS_TOKEN` for SDK-direct. | Create a Genie space, grant `CAN RUN`, set the secrets, run `-f require_databricks=true`. |
| **Published site** | `ran` on every push | The published workshop site is reachable. | none | Automatic — no secrets. |
| **Offline readiness** | `ran` on every push | `demo_check.py`, offline eval, and artifact generation succeed without any cloud. | none | Automatic — runs on every push. |
| **Recorded/offline backend E2E** | `ran` on every push | Recorded Fabric- and Databricks-shaped WWI rows flow through the **real** normalize → quota → report path and produce non-empty XLSX/HTML/PDF artifacts with source-specific citations. | none | Automatic — `python scripts/recorded_live_proof.py`. |

### Recorded vs. live: what the offline proof does and does not cover

The **recorded/offline backend E2E proof** (`scripts/recorded_live_proof.py`) closes a specific gap: in demo
mode the live Fabric and Databricks jobs are `skipped`, so nothing exercises the end-to-end pipeline for those
backend row shapes. The recorded proof replays non-secret, backend-shaped fixtures
(`src/agents/quota_estimator/recorded_fixtures/`) through the **same** code path the live backends feed —
`generate_quota_estimation_report` — and asserts that each platform's column contract normalizes, produces
quota recommendations, and writes real XLSX/HTML/PDF artifacts with the correct per-source citation and
methodology.

Run it locally:

```powershell
python scripts/recorded_live_proof.py          # human-readable summary
python scripts/recorded_live_proof.py --json    # machine-readable result
```

:::warning Recorded ≠ live
The recorded proof is **offline**. It never contacts Fabric or Databricks, so it is reported in its own
`recorded-offline` category — never as a `live-backend` check — and a passing recorded proof must not be read
as a live connection being validated. It proves the *pipeline and report path* are correct for each backend's
row shape; it does **not** replace the live golden-QA eval or Genie query. Those stay gated on real secrets
above.
:::

:::warning Skipped ≠ proven
Treat `skipped` as **unvalidated**, not "working". The offline gate and unit tests cover tool contracts,
quota math, and artifact generation deterministically, but they do not prove a live Fabric, Databricks, or
Foundry round trip. Before a customer delivery, set the secrets for the platform you teach and run that
backend in **required mode** so a skip turns the run red.
:::

:::warning Out of scope for an autonomous agent
Creating the federated credential mutates Microsoft Graph and may trigger an interactive Conditional Access /
CAE challenge that a headless agent cannot satisfy. In that case the setup script prints the manual command —
a facilitator runs it once, and subsequent runs are green.
:::

See the [Troubleshooting](troubleshooting#oidc-and-live-smoke) page for specific OIDC and required-mode errors.
