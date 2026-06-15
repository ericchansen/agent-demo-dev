---
sidebar_position: 9
title: Foundry Local and DevUI
---

# Foundry Local and DevUI

:::info Optional Day 2 lab
Use this path when cloud access is blocked, when attendees need to debug orchestration before registering agents, or
when you want a safe comparison between offline proof, local model runtime, and live Foundry Agent Service.
:::

Foundry Local is an on-device model runtime with an OpenAI-compatible local endpoint. It is useful for prototyping
model calls without an Azure round trip, but it is **not** a replacement for the Foundry portal, agent registration,
or hosted multi-agent tracing. The multi-agent debugging experience in this repo comes from deterministic pipeline
output, JSON stage traces, unit tests, and the optional Microsoft Agent Framework runtime.

## Runtime choices

| Runtime | What runs | Needs cloud? | What it proves |
|---|---|---|---|
| Deterministic pipeline | `planner -> data -> research -> work-context -> conversation -> report` in Python | No | Tool contracts, row normalization, artifact generation, and routing shape. |
| Foundry Local | Local model service for OpenAI-compatible calls | No | A local model can answer prompts; useful for prompt experiments, not portal registration proof. |
| Agent Framework + Foundry | Microsoft Agent Framework over `FoundryChatClient` | Yes | Live model orchestration against the account-based project. |
| Foundry portal | Registered agent, Playground, traces, evals, publish | Yes | Production path for Day 2 and Microsoft 365 publishing. |

## 1. Run the deterministic DevUI-style trace

The fastest offline loop is the deterministic multi-agent pipeline. It prints a JSON object with the selected agents,
data source, sales rows, response text, and generated artifacts.

```powershell
uv run python -m src.orchestrator.multi_agent `
  "Generate a quota report for Tailspin Toys" `
  --customer "Tailspin Toys" `
  --data-source fabric `
  --output-dir output/foundry-local-devui/fabric

uv run python -m src.orchestrator.multi_agent `
  "Generate a quota report for Tailspin Toys" `
  --customer "Tailspin Toys" `
  --data-source databricks `
  --output-dir output/foundry-local-devui/databricks
```

Open the JSON output like a lightweight DevUI trace:

| JSON field | Debugging use |
|---|---|
| `agent_sequence` | Confirms the planner, data, research, work-context, conversation, and report stages are wired. |
| `data_source` / `sales_rows` | Confirms Fabric-shaped or Databricks-shaped rows normalize into the shared contract. |
| `quota_report.methodology` | Confirms the report cites the selected data platform and scenario assumptions. |
| `quota_report.artifacts` | Confirms XLSX, HTML, and PDF files were generated under `output/`. |

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

Foundry Local exposes a local service for OpenAI-compatible development, but this repo keeps the default offline lab
deterministic so every participant gets identical quota math and artifacts.

## 3. Compare with the live Agent Framework runtime

When the Foundry project and model deployment are ready, switch from deterministic orchestration to the live Agent
Framework path:

```powershell
uv sync --extra agent-framework
$env:FOUNDRY_PROJECT_ENDPOINT="https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
$env:MODEL_DEPLOYMENT_NAME="gpt-4o"

uv run python -m src.orchestrator.multi_agent `
  "Generate a quota report for Tailspin Toys" `
  --customer "Tailspin Toys" `
  --data-source fabric `
  --runtime agent-framework
```

This invokes Microsoft Agent Framework participants over `FoundryChatClient`. It still is not equivalent to portal
publish proof: after this works, register the Foundry agent, run the Playground prompt, inspect traces, and run the
evaluation lab.

## 4. Optional helper script

Windows facilitators can run the deterministic checks and inspect Foundry Local installation status with:

```powershell
.\scripts\run_foundry_local_demo.ps1
.\scripts\run_foundry_local_demo.ps1 -DataSource databricks -CustomerName "Tailspin Toys"
```

The script intentionally does not start a long-running service or download a model for attendees. Model choice,
license, and hardware fit are facilitator decisions.

## References

- [Foundry Local documentation](https://learn.microsoft.com/en-us/azure/foundry-local/)
- [Foundry Local overview](https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local)
- [Foundry Local CLI reference](https://learn.microsoft.com/en-us/azure/foundry-local/reference/reference-cli)
- [Agent Framework sequential orchestration](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential)
