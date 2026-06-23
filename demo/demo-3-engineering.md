# Demo 3 — Engineering Deep Dive (30 minutes)

> **Audience:** Engineering teams evaluating for adoption
> **Goal:** Walk through codebase, IaC, testing, and extensibility
> **Focus:** Prove this is production-ready, not just a prototype

---

## Prerequisites

| Requirement | Details |
|---|---|
| Repo cloned | `git clone` + `uv sync` |
| Python 3.11+ | Virtual environment activated |
| Azure CLI | Authenticated (`az login`) |
| Fabric capacity | F2+ for live queries (optional — recorded fixtures available) |
| VS Code | Python + Copilot extensions |

### Pre-flight checklist (15 min before)

- [ ] `make lint` — zero errors
- [ ] `make test` — all unit tests pass
- [ ] Open repo in VS Code with file explorer visible
- [ ] Terminal ready at repo root
- [ ] `az bicep build --file infra/main.bicep` — compiles clean

---

## Section 1 — Repo Structure (4 minutes)

### 1. AGENTS.md

> **Say:**
> "Every project starts with AGENTS.md. It's the entry point for any developer — or AI coding agent — to understand the architecture, standards, and key directories."

### 2. Directory walkthrough

`
src/
├── orchestrator/       # Foundry agent definition + tool schemas
├── agents/             # Quota estimator pipeline
├── cli/                # MCP config + skills for Copilot CLI
infra/                  # Bicep IaC (one-click deployment)
fabric/                 # Data Agent config + few-shot examples
tests/                  # Unit + eval tests
`

---

## Section 2 — The Agent (8 minutes)

### 3. Foundry agent definition

Open `src/orchestrator/foundry_agent.py`:

> **Point out:**
> - Agent name and instructions (line ~56)
> - Tool registration (FabricIQ, market data, quota forecast)
> - Instruction builder pattern — conditional sections based on config

### 4. Tool schemas

Open `src/orchestrator/tool_schemas.py`:

> **Point out:**
> - JSON Schema definitions for each tool
> - How these map to both MCP (CLI) and FunctionTool (Foundry)

### 5. Quota estimator pipeline

Open `src/agents/quota_estimator/pipeline.py`:

> **Say:**
> "This is the core business logic — scenario modeling, revenue projection, methodology documentation. It's pure Python, testable in isolation, and produces structured output that any surface can render."

---

## Section 3 — Infrastructure (5 minutes)

### 6. IaC

Open `infra/main.bicep`:

> **Point out:**
> - Single entry point deploys everything (Foundry project, Key Vault, identity)
> - Demo defaults: public access enabled, no policy assignments
> - Production toggle: flip parameters for network isolation + RBAC

### 7. Deploy (if time)

`ash
az deployment group create \
  --resource-group rg-sales-agent-demo \
  --template-file infra/main.bicep \
  --parameters env=dev
`

---

## Section 4 — Testing (5 minutes)

### 8. Unit tests

`ash
make test  # runs: pytest tests/unit/ -q
`

> **Point out:**
> - 151 tests, all pass in ~10 seconds
> - Recorded fixtures for offline testing (no Fabric needed)
> - Mock patterns for external services

### 9. Eval tests

Open `tests/eval/run_eval.py`:

> **Say:**
> "Evaluation tests run actual queries against the agent and grade the responses. They're separate from unit tests — you run them against a live environment to validate answer quality."

---

## Section 5 — Extensibility (5 minutes)

### 10. Adding a new skill

> **Walk through:**
> 1. Create a skill .md file in src/cli/skills/
> 2. Register the MCP server in src/cli/mcp-config.json
> 3. Add the tool schema in src/orchestrator/tool_schemas.py
> 4. Write a unit test

### 11. Adding a new data source

> **Walk through:**
> 1. Add a recorded fixture in src/agents/quota_estimator/recorded_fixtures/
> 2. Create a DataSource class implementing the standard interface
> 3. Wire it into the pipeline

---

## Wrap up (3 minutes)

> **Say:**
> "You've seen the full stack — from a simple M365 Copilot query to the Python pipeline underneath, the Bicep infrastructure, and 151 passing tests. This is a working reference, not a slide deck. Clone it, deploy it, extend it."