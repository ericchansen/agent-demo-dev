---
sidebar_position: 8
title: Evaluation and Trace Replay
---

# Evaluation and Trace Replay

:::info[Where you are · 🗓️ Day 2]

Use this lab after the agent is visible in Azure AI Foundry and before publishing to Microsoft 365. The goal is to
turn one good trace and one failure trace into repeatable regression checks.
:::

Foundry evaluations make the workshop operational: you no longer trust a demo because it worked once in the
Playground. You keep a small golden set, replay traces when behavior changes, and compare scores before and after an
instruction or tool-contract tweak.

## Files in this repo

| File | Purpose |
|---|---|
| `evals/sales-agent/eval.yaml` | Foundry-native eval configuration for the Sales Agent. |
| `evals/sales-agent/datasets/golden-prompts.jsonl` | Golden prompts covering Fabric, Databricks, scenario control, artifacts, and trace-to-eval conversion. |
| `evals/sales-agent/rubrics/quota-quality.md` | Human-readable rubric for quota-report quality. |

The eval is environment-driven. Keep tenant-specific values in your private `.env` or shell profile:

```powershell
$env:FOUNDRY_PROJECT_ENDPOINT="https://<ai-services-account>.services.ai.azure.com/api/projects/<project-name>"
$env:MODEL_DEPLOYMENT_NAME="gpt-4o"
```

## 1. Run one golden query

Start with the same prompt in the Playground and CLI so participants can compare surfaces:

```powershell
uv run python scripts/verify_foundry_agent.py
uv run python -m src.orchestrator "Generate a base quota estimation report for Tailspin Toys"
```

In the Foundry portal, open the project from `FOUNDRY_PROJECT_ENDPOINT`, choose **Agents**, open `SalesAgent`,
and run the Tailspin Toys prompt in the Playground.

## 2. Inspect the trace

Open the trace or observability view for the Playground run. Capture these facts in private facilitator notes:

| Trace field | What to confirm |
|---|---|
| Input | The prompt names the customer, scenario, and data platform clearly. |
| Tool calls | The agent selected Fabric Data Agent, Databricks Genie, or an explicit configuration-block path. |
| Output | The response cites the data source, scenario, methodology, and artifact plan. |
| Safety | No secrets, tenant IDs, or sensitive payloads appear in shared notes. |

## 3. Convert the trace into an eval case

If the trace is a keeper, add a minimal case to `evals/sales-agent/datasets/golden-prompts.jsonl`. If the trace failed,
write the desired behavior as `expected_traits` instead of copying the bad answer. Keep the prompt short enough that
it can be rerun after every instruction change.

Example JSONL row:

```json
{"name":"quota-base-tailspin","prompt":"Generate a base quota estimation report for Tailspin Toys using trailing sales, market context, and WorkIQ activity.","criteria":[{"name":"scenario","instruction":"The response uses the base scenario."},{"name":"artifacts","instruction":"The response mentions XLSX, HTML, and PDF artifacts."}]}
```

## 4. Run the Foundry eval

Install or update the Azure Developer CLI extension that provides agent evaluations, then run the eval from the
`evals/sales-agent` folder:

```powershell
azd auth login
azd extension install azure.ai.agents
cd evals/sales-agent
azd ai agent eval update
azd ai agent eval run --config eval.yaml
```

The current Microsoft command surface is documented in
[Run agent evaluations with the azd CLI](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/azure-developer-cli-evaluation).
If your installed `azd` build does not expose `azd ai agent eval`, update `azd`, install the `azure.ai.agents`
extension, and record the tool version in facilitator notes. Agent Optimizer commands are limited preview; the eval
run/update loop is the workshop requirement.

## 5. Compare before and after a tweak

Use the eval score as the Day 2 regression loop:

1. Run the eval and save the score summary.
2. Change one thing: agent instruction, Genie/Fabric row-contract instruction, or quota tool schema.
3. Re-register the agent with `uv run python scripts/verify_foundry_agent.py`.
4. Re-run `azd ai agent eval run --config eval.yaml`.
5. Keep the change only if the quota-quality score improves or stays above threshold without hurting groundedness.

## Offline fallback

Foundry-native evals require a live project. When cloud access is blocked, use the deterministic offline gate:

```powershell
uv run python tests/eval/run_eval.py --mock --pass-rate 100
```

Offline evals prove the Fabric golden-QA harness and deterministic quota math. They do **not** prove live Foundry
registration, model behavior, or portal trace replay.
