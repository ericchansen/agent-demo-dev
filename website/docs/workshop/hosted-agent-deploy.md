---
sidebar_position: 8
title: Deploy the Hosted Agent
---

# Deploy the Hosted Agent

The **hosted agent** (`src/orchestrator/hosted_agent/`) is the bring-your-own-code path for production. It
packages the same Fabric/Databricks, quota, research, attainment, activity, and report tools behind a single
managed-container endpoint, and it is the agent you publish to Microsoft 365 Copilot and Teams (a prompt agent
registered by `verify_foundry_agent.py` cannot be published directly — see
[Troubleshooting → Microsoft 365 publishing](troubleshooting#microsoft-365-publishing)).

This lab takes the container from **build → run locally → deploy → test**. Every command is copy-paste ready.

:::info Where you are · 🗓️ Day 2
The hosted agent is the Day 2 production deployment. Do the [Foundry Surface](../architecture/foundry-surface)
registration first so you understand the account-based project and model deployment this container talks to.
:::

## What the container exposes

The server (`src/orchestrator/hosted_agent/server.py`) is a transport-thin HTTP layer. The routing logic lives
in `route_request`, which is unit-tested without sockets (`tests/unit/test_hosted_server.py`).

| Method & path | Purpose | Success response |
|---|---|---|
| `GET /healthz` | Liveness probe | `200 {"status":"alive"}` |
| `GET /readyz` | Readiness probe (reports adapter) | `200 {"status":"ready","adapter":"..."}` |
| `GET /readiness` | Foundry Hosted Agent readiness alias | `200 {"status":"ready","adapter":"..."}` |
| `GET /` | Legacy health payload | `200 {"status":"healthy","agent":"wwi-sales-hosted"}` |
| `POST /invoke` (or `/`) | Invocations protocol | `200 {"output":"..."}` |
| `POST /responses` | OpenAI-compatible Responses protocol | `200 {"object":"response","output_text":"...",...}` |

Every response carries an `X-Request-Id` header (echoed from the request or freshly minted). The
[deployment definition](https://github.com/ericchansen/agent-demo-dev/blob/main/src/orchestrator/hosted_agent/agent.yaml)
declares both `responses` and `invocations` protocols. The server exposes `/healthz`, `/readyz`, and the Foundry
`/readiness` alias. A unit test
(`tests/unit/test_hosted_agent_manifest.py`) keeps the manifest and the server in sync.

## 1. Validate locally before you build

The hosted runtime ships a `LocalDeterministicAdapter`, so it runs with **no model credentials**. Validate the
contract first:

```powershell
pytest tests/unit/test_hosted_server.py tests/unit/test_hosted_agent.py tests/unit/test_hosted_agent_manifest.py -q
```

All three suites should pass. This proves routing, tool dispatch, and the manifest/server contract before you
spend time on a container build.

## 2. Run the server locally

```powershell
# From the repo root — the local runtime adapter needs no secrets.
python -m src.orchestrator.hosted_agent.server
```

In a second terminal, exercise both protocols:

```powershell
# Liveness / readiness
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/readyz
curl http://127.0.0.1:8088/readiness

# Invocations protocol
curl -X POST http://127.0.0.1:8088/invoke `
  -H "Content-Type: application/json" `
  -d '{"input":"Compute quota attainment: target 1,000,000, ytd 600,000, pipeline 500,000, 6 months, 180 days"}'

# Responses protocol (OpenAI-compatible, non-streaming)
curl -X POST http://127.0.0.1:8088/responses `
  -H "Content-Type: application/json" `
  -d '{"input":"Forecast quota for Tailspin Toys"}'
```

Expected: `/healthz` → `{"status":"alive"}`, `/readyz` or `/readiness` →
`{"status":"ready","adapter":"..."}`, `/invoke` →
`{"output":"..."}`, `/responses` → a `{"object":"response","status":"completed","output_text":"..."}` payload.
Sending `Content-Type: text/plain` returns `415`; the server accepts the `stream` flag used by `azd ai agent invoke`
and still returns a completed JSON payload.

## 3. Build the container

The [Dockerfile](https://github.com/ericchansen/agent-demo-dev/blob/main/src/orchestrator/hosted_agent/Dockerfile)
installs `requirements-hosted.txt`, copies `src/`, `schemas/`, and `fabric/`, exposes `8088`, and declares a
`HEALTHCHECK` against `/healthz`. Build it from the **repo root** (the build context needs `src/`):

```powershell
docker build -t wwi-hosted-agent:dev -f src/orchestrator/hosted_agent/Dockerfile .
```

Run it and confirm Docker reports the container **healthy** (the HEALTHCHECK polls `/healthz`):

```powershell
docker run --rm -p 8080:8088 --name wwi-hosted wwi-hosted-agent:dev
# in another terminal:
docker ps --filter name=wwi-hosted --format "{{.Status}}"   # -> "Up ... (healthy)"
curl http://127.0.0.1:8080/readyz
```

For live model-backed runs, pass the same environment the manifest declares:

```powershell
docker run --rm -p 8080:8088 `
  -e FOUNDRY_PROJECT_ENDPOINT=$env:FOUNDRY_PROJECT_ENDPOINT `
  -e AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o `
  -e HOSTED_AGENT_ADAPTER=auto `
  wwi-hosted-agent:dev
```

| Variable | Purpose |
|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint injected by the hosted platform; set locally for model-backed runs |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment name (defaults to `gpt-4o` in the deployment definition) |
| `MODEL_ENDPOINT` / `MODEL_DEPLOYMENT` | Local aliases still accepted by the adapter |
| `HOSTED_AGENT_ADAPTER` | Deployment default is `local` for deterministic workshop smoke tests; set `auto` or `azure` after granting the hosted identity Foundry model permissions |
| `FABRIC_MCP_URL` / `FABRIC_MCP_TOOL_NAME` | Live Fabric Data Agent MCP wiring |
| `HOSTED_AGENT_OUTPUT_DIR` | Where generated quota artifacts are written |

## 4. Deploy to Azure AI Foundry

Hosted agents are a **Public Preview** Foundry capability. There are two supported deployment paths — the `azd`
extension flow (recommended for the workshop) and a manual container push. Pick one.

### 4a. Recommended: the `azd ai agent` preview flow

The Foundry azd extension wraps init → local test → deploy → invoke → monitor. Install it once (needs `azd` ≥
1.25.3):

```powershell
azd ext install microsoft.foundry
```

| Command | What it does |
|---|---|
| `azd ai agent init` | Scaffolds the agent project (`azure.yaml` with a `startupCommand`, an `agent.manifest.yaml`) from a manifest. Add `--deploy-mode code` to use the **source-code ZIP** path (no Dockerfile — the platform builds your Python 3.13/3.14 or .NET 10 source). |
| `azd ai agent run` | Creates a venv, installs deps, runs the agent locally, and opens the **Agent Inspector** browser UI. Pass `--no-inspector` for headless. |
| `azd deploy` | Builds + pushes the container to ACR and registers a new **agent version** in Foundry Agent Service. (There is **no** `azd ai agent deploy` subcommand — use `azd deploy`.) |
| `azd ai agent invoke "<prompt>"` | Sends a prompt to the **deployed** agent and prints the response. |
| `azd ai agent monitor --follow` | Streams live container logs from the deployed agent. |

:::note Source-code vs container
`--deploy-mode code` (source ZIP) and the container image path are both preview. This repo ships a real
[Dockerfile](https://github.com/ericchansen/agent-demo-dev/blob/main/src/orchestrator/hosted_agent/Dockerfile), so
the container path below works today and gives you full control over the runtime. See
[Deploy a hosted agent from source code](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent-code)
for the ZIP alternative.
:::

### 4b. Manual: push the container yourself

Push the image to a registry the Foundry account can pull, then register the agent version. Substitute your
registry and resource names:

```powershell
# Push to Azure Container Registry
az acr login -n <registry>
docker tag wwi-hosted-agent:dev <registry>.azurecr.io/wwi-hosted-agent:dev
docker push <registry>.azurecr.io/wwi-hosted-agent:dev
```

Register the image as an agent version on the account-based Foundry project (the same
`https://<account>.services.ai.azure.com/api/projects/<project>` endpoint the SDK uses) via the portal, Python/.NET
SDK, or REST. Follow the current flow in
[Deploy a hosted agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent) and
point the image at the tag you pushed. When the version reaches **active**, the hosted agent receives a **dedicated
Entra agent identity** and a `{project_endpoint}/agents/<name>/endpoint` URL — that identity is what makes the
Microsoft 365 / Teams publish path work.

### 4c. Wire connections (Fabric / Databricks / Azure OpenAI)

The container reads live backends through Foundry **connections** — named references to external services you
create on the project. Core types (Azure OpenAI, Azure AI Search, Storage, Application Insights) are GA;
**Microsoft Fabric and Azure Databricks connections are preview and are created via code/Bicep only** (not the
portal UI), then referenced by **connection name**. Use these as placeholders when you template the deployment:

```powershell
# Names you assign at creation time; reference them from agent config / env, not by resource ID.
$env:FOUNDRY_AOAI_CONNECTION   = "<azure-openai-connection-name>"
$env:FOUNDRY_FABRIC_CONNECTION = "<fabric-connection-name>"      # preview, code/Bicep only
$env:FOUNDRY_DATABRICKS_CONNECTION = "<databricks-connection-name>"  # preview, code/Bicep only
```

See [Add a new connection to your project](https://learn.microsoft.com/en-us/azure/foundry/how-to/connections-add)
for the current type list and auth options.

## 5. Test the deployed endpoint

Once Foundry reports the agent **active / Ready**, test it three ways:

**CLI status + invocation:**

```powershell
azd ai agent show wwi-sales-hosted --output json
azd ai agent invoke wwi-sales-hosted "Generate a quota report for Tailspin Toys" --protocol responses
```

**Agent Inspector (local):** `azd ai agent run` opens the **Foundry Toolkit Agent Inspector** in your browser (or
press **F5** in VS Code with the Microsoft Foundry Toolkit extension). It's a local dev surface for interactive
chat and breakpoints against the running container — not an in-portal feature.

**Agents playground + tracing (portal):** In the Foundry portal, open the **Agents playground** to chat with the
deployed agent, then read the **Agent tracing** tab to inspect end-to-end spans — every model call and tool
execution, with latency and token usage (backed by Application Insights). The playground is GA for prompt agents
and **preview** for hosted agents.

A healthy deployment returns `alive` / `ready` on the probes and a completed Responses payload whose `output_text`
contains the quota summary. The published path then surfaces the same agent in M365 Copilot Chat and Teams via
Foundry's Responses → Activity bridge.

> 📖 [Agents playground](https://learn.microsoft.com/en-us/azure/foundry/concepts/concept-playgrounds) ·
> [Agent tracing](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept) ·
> [Hosted agent quickstart](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent)

## 6. Promote new versions safely

Hosted agents use **discrete versions** (`v1`, `v2`, …). When you deploy an update, requests go to one active
version at a time.

:::warning No traffic split for hosted agents
Foundry Agent Service hosted agents **do not** support canary, blue-green, or weighted traffic splitting — there is
no `--traffic` flag or equivalent. The safe-promotion pattern is: deploy the new version, smoke-test it with
`azd ai agent invoke` / the probes / the Agents playground, then cut M365/Teams publishing over to it. Keep the
previous version registered so you can roll back by re-pointing at it.
:::

If you genuinely need weighted **traffic splitting / blue-green**, that capability lives in a *different* resource —
**Azure Machine Learning managed online endpoints** (GA), not Foundry Agent Service:

```powershell
# Azure ML managed online endpoints ONLY — not Foundry hosted agents.
az ml online-endpoint update --name <endpoint> --traffic "blue=90 green=10"
az ml online-endpoint update --name <endpoint> --mirror-traffic "green=10"   # shadow up to 50%
```

See [Safe rollout for online endpoints](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-safely-rollout-online-endpoints?view=azureml-api-2).
For the hosted-agent versioning model, see
[Hosted agents in Azure AI Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `session_not_ready` from `azd ai agent invoke` | Confirm the container listens on `8088` and that `/readiness` returns HTTP 200 locally. |
| `/readyz` reports `adapter unavailable` | Model env vars missing; set `FOUNDRY_PROJECT_ENDPOINT` / `AZURE_AI_MODEL_DEPLOYMENT_NAME` (or local aliases `MODEL_ENDPOINT` / `MODEL_DEPLOYMENT`), or run the credential-free local runtime. |
| `415 unsupported_media_type` | Send `Content-Type: application/json`. |
| `413 payload_too_large` | Invocation bodies are capped at 1 MiB. |
| Container build can't find `src/` | Build from the **repo root** with `-f src/orchestrator/hosted_agent/Dockerfile .`. |

More entries on the [Troubleshooting](troubleshooting#hosted-agent) page.
