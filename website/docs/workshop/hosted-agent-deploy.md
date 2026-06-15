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
| `GET /` | Legacy health payload | `200 {"status":"healthy","agent":"wwi-sales-hosted"}` |
| `POST /invoke` (or `/`) | Invocations protocol | `200 {"output":"..."}` |
| `POST /responses` | OpenAI-compatible Responses protocol | `200 {"object":"response","output_text":"...",...}` |

Every response carries an `X-Request-Id` header (echoed from the request or freshly minted). The
[deployment manifest](https://github.com/ericchansen/agent-demo-dev/blob/main/src/orchestrator/hosted_agent/agent.yaml)
declares both `responses` and `invocations` protocols and the `/healthz` / `/readyz` probes. A unit test
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
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/readyz

# Invocations protocol
curl -X POST http://127.0.0.1:8080/invoke `
  -H "Content-Type: application/json" `
  -d '{"input":"Compute quota attainment: target 1,000,000, ytd 600,000, pipeline 500,000, 6 months, 180 days"}'

# Responses protocol (OpenAI-compatible, non-streaming)
curl -X POST http://127.0.0.1:8080/responses `
  -H "Content-Type: application/json" `
  -d '{"input":"Forecast quota for Tailspin Toys"}'
```

Expected: `/healthz` → `{"status":"alive"}`, `/readyz` → `{"status":"ready","adapter":"..."}`, `/invoke` →
`{"output":"..."}`, `/responses` → a `{"object":"response","status":"completed","output_text":"..."}` payload.
Sending `Content-Type: text/plain` returns `415`; sending `{"stream":true}` to `/responses` returns
`400 streaming_not_supported`.

## 3. Build the container

The [Dockerfile](https://github.com/ericchansen/agent-demo-dev/blob/main/src/orchestrator/hosted_agent/Dockerfile)
installs `requirements-hosted.txt`, copies `src/`, `schemas/`, and `fabric/`, exposes `8080`, and declares a
`HEALTHCHECK` against `/healthz`. Build it from the **repo root** (the build context needs `src/`):

```powershell
docker build -t wwi-hosted-agent:dev -f src/orchestrator/hosted_agent/Dockerfile .
```

Run it and confirm Docker reports the container **healthy** (the HEALTHCHECK polls `/healthz`):

```powershell
docker run --rm -p 8080:8080 --name wwi-hosted wwi-hosted-agent:dev
# in another terminal:
docker ps --filter name=wwi-hosted --format "{{.Status}}"   # -> "Up ... (healthy)"
curl http://127.0.0.1:8080/readyz
```

For live model-backed runs, pass the same environment the manifest declares:

```powershell
docker run --rm -p 8080:8080 `
  -e MODEL_ENDPOINT=$env:FOUNDRY_PROJECT_ENDPOINT `
  -e MODEL_DEPLOYMENT=gpt-4o `
  -e HOSTED_AGENT_ADAPTER=auto `
  wwi-hosted-agent:dev
```

| Variable | Purpose |
|---|---|
| `MODEL_ENDPOINT` | Foundry project endpoint for the injected chat adapter |
| `MODEL_DEPLOYMENT` | Model deployment name (defaults to `gpt-4o`) |
| `HOSTED_AGENT_ADAPTER` | `auto` selects a model adapter when configured, else the local runtime |
| `FABRIC_MCP_URL` / `FABRIC_MCP_TOOL_NAME` | Live Fabric Data Agent MCP wiring |
| `HOSTED_AGENT_OUTPUT_DIR` | Where generated quota artifacts are written |

## 4. Deploy to Azure AI Foundry

Push the image to a registry the Foundry account can pull, then deploy the manifest. Substitute your registry
and resource names:

```powershell
# Push to Azure Container Registry
az acr login -n <registry>
docker tag wwi-hosted-agent:dev <registry>.azurecr.io/wwi-hosted-agent:dev
docker push <registry>.azurecr.io/wwi-hosted-agent:dev
```

Deploy `agent.yaml` to the account-based Foundry project (the same
`https://<account>.services.ai.azure.com/api/projects/<project>` endpoint the SDK uses). Hosted Agents are a
preview Foundry feature; follow the current portal/CLI flow in
[Hosted agents in Azure AI Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) and
point the container image at the tag you pushed. When deployed, the hosted agent receives a **dedicated Entra
agent identity**, which is what makes the Microsoft 365 / Teams publish path work.

## 5. Test the deployed endpoint

Once Foundry reports the agent **Ready**, run the same probes against the managed endpoint:

```powershell
curl https://<your-hosted-endpoint>/healthz
curl https://<your-hosted-endpoint>/readyz
curl -X POST https://<your-hosted-endpoint>/responses `
  -H "Content-Type: application/json" `
  -d '{"input":"Generate a quota report for Tailspin Toys"}'
```

A healthy deployment returns `alive` / `ready` on the probes and a completed Responses payload whose
`output_text` contains the quota summary. The published path then surfaces the same agent in M365 Copilot Chat
and Teams via Foundry's Responses → Activity bridge.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/readyz` reports `adapter unavailable` | Model env vars missing; set `MODEL_ENDPOINT` / `MODEL_DEPLOYMENT`, or run the credential-free local runtime. |
| `415 unsupported_media_type` | Send `Content-Type: application/json`. |
| `400 streaming_not_supported` | The Responses route is non-streaming; send `stream=false` (or omit it). |
| `413 payload_too_large` | Invocation bodies are capped at 1 MiB. |
| Container build can't find `src/` | Build from the **repo root** with `-f src/orchestrator/hosted_agent/Dockerfile .`. |

More entries on the [Troubleshooting](troubleshooting#hosted-agent) page.
