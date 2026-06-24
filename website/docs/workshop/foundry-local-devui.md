---
sidebar_position: 9
title: Foundry Local and DevUI
---

# Foundry Local and DevUI

:::info[Optional Day 2 lab]

Use this path when cloud access is blocked, when attendees need to debug orchestration before registering agents, or
when you want a safe comparison between offline proof, local model runtime, and live Foundry Agent Service.
:::

Foundry Local is an on-device model runtime with an OpenAI-compatible local endpoint. It is useful for prototyping
model calls without an Azure round trip, but it is **not** a replacement for the Foundry portal, agent registration,
or hosted tracing. Offline confidence in this repo comes from the unit and contract test suite; live orchestration
comes from the registered `SalesAgent`.

## Runtime choices

| Runtime | What runs | Needs cloud? | What it proves |
|---|---|---|---|
| Test suite | `pytest` unit + contract tests | No | Tool contracts, row normalization, artifact generation, and routing shape. |
| Foundry Local | Local model service for OpenAI-compatible calls | No | A local model can answer prompts; useful for prompt experiments, not portal registration proof. |
| Foundry SalesAgent | `python -m src.orchestrator` over the live project | Yes | Live model orchestration of internal + external tools against the account-based project. |
| Foundry portal | Registered agent, Playground, traces, evals, publish | Yes | Production path for Day 2 and Microsoft 365 publishing. |

## 1. Validate offline with the test suite

The fastest offline loop needs no Azure round trip. The unit and contract tests exercise the tool contracts, the
shared sales-row normalization, and report generation:

```powershell
uv sync --extra dev
uv run python -m pytest tests/unit -q
```

These tests confirm Fabric-shaped and Databricks-shaped rows normalize into the shared quota contract and that XLSX,
HTML, and PDF artifacts generate correctly — without registering an agent.

## 2. Install Foundry Local for local model experiments

Install Foundry Local only if the lab needs local model inference:

```powershell
winget install Microsoft.FoundryLocal
foundry --version
foundry service status
foundry model list
```

Download and run a small model that fits your machine:

```powershell
foundry model download <model-alias>
foundry model run <model-alias>
```

Foundry Local exposes a local OpenAI-compatible service for development, but this repo keeps the default lab
cloud-free through the test suite so every participant gets identical results.

## 3. Go live with the registered agent

When the Foundry project and model deployment are ready, run the single `SalesAgent` workflow against the live
project and verify the registration:

```powershell
$env:FOUNDRY_PROJECT_ENDPOINT="https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
$env:MODEL_DEPLOYMENT_NAME="gpt-4o"

uv run python -m src.orchestrator "Generate a quota report for Tailspin Toys"
uv run python scripts/verify_foundry_agent.py
```

`verify_foundry_agent.py` registers the prompt agent, runs a Playground-style Responses query, and exits non-zero on
failure. After this works, open the Foundry portal to inspect traces, run the evaluation lab, and publish to
Microsoft 365 and Teams.

For a code-first multi-agent option, install the Agent Framework extra (`uv sync --extra agent-framework`) and compose
participants with `SequentialBuilder` as described in [the Foundry surface](../architecture/foundry-surface).

## References

- [Foundry Local documentation](https://learn.microsoft.com/en-us/azure/foundry-local/)
- [Foundry Local overview](https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local)
- [Foundry Local CLI reference](https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-cli)
- [Agent Framework sequential orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential)
