# Demo 3 — Engineering Deep Dive (30 minutes)

> **Audience:** Engineering teams evaluating the solution for adoption
> **Goal:** Walk through the codebase, IaC, testing, and extensibility — prove this is production-ready
> **Dataset:** Wide World Importers (wholesale novelty goods)

---

## Prerequisites

| Requirement | Details |
|---|---|
| Repo cloned | `git clone` + `cd fabric-sales-agent-accelerator-scaffold` |
| Python 3.11+ | Virtual environment activated, `pip install -r requirements.txt` |
| Azure CLI | Authenticated (`az login`) |
| Fabric capacity | F2 or higher for live Data Agent queries (optional — mock mode available) |
| VS Code | With Python extension, Copilot extension |
| Make | For running Makefile targets |

### Pre-flight checklist (do this 15 min before the demo)

- [ ] Run `make lint` — confirm zero errors
- [ ] Run `make test` — confirm all unit tests pass
- [ ] Open the repo in VS Code with the file explorer visible
- [ ] Have a terminal ready at the repo root
- [ ] Pre-run `make infra-validate` so Bicep compilation is cached
- [ ] Have `docs/costs.md` open in a tab for the cost discussion

---

## Section 1 — Repo Structure (4 minutes)

### 1. Start with AGENTS.md (1 minute)

Open `AGENTS.md` in VS Code:

> **Say:**
> "Every repo in this accelerator pattern starts with AGENTS.md. This is the entry point for any developer — or any AI coding agent — that needs to understand the project. It covers the architecture, coding standards, key directories, and important design decisions."

Highlight the key sections:
- Four sub-agents (Fabric Data Agent, Researcher, SharePoint, Report Generator)
- Four consumption surfaces
- "LLM-agnostic" and "citations first-class" design principles

### 2. Directory walkthrough (3 minutes)

Show the top-level directory tree:

```
fabric-sales-agent-accelerator-scaffold/
├── src/
│   ├── agents/           # Sub-agent MCP servers
│   │   ├── researcher/   # Web research (mcp_server.py + tools.py)
│   │   ├── sharepoint/   # Internal docs (mcp_server.py + tools.py)
│   │   └── report_generator/  # DOCX/PPTX generation (templates/)
│   ├── orchestrator/     # Azure AI Foundry orchestrator
│   └── cli/              # Copilot CLI skill definitions
├── infra/                # Bicep IaC
│   ├── main.bicep
│   ├── modules/          # Modular: entra-app, fabric-capacity, keyvault
│   └── parameters/       # Per-environment parameter files
├── fabric/               # Fabric Data Agent config, instructions, few-shot
├── demo/                 # Sample data, screenshots, demo scripts
├── docs/                 # Architecture, security, surfaces, costs
├── tests/
│   ├── unit/             # Fast, mock everything
│   ├── integration/      # MCP protocol verification
│   └── eval/             # LLM output quality scoring
├── Makefile              # All commands: lint, test, deploy, serve, etc.
├── AGENTS.md             # AI-readable project guide
└── pyproject.toml        # Python project config (ruff, mypy, pytest)
```

> **Say:**
> "Standard Python project layout. `src/agents/` has the custom MCP servers. `infra/` is Bicep — Azure-native IaC. `tests/` has three tiers: unit, integration, and eval. The Makefile is the single entry point for everything."

---

## Section 2 — Infrastructure as Code (5 minutes)

### 3. Validate Bicep (1 minute)

```bash
make infra-validate
```

> **Say:**
> "This runs `az bicep build` — it compiles the Bicep to ARM and validates the syntax. Zero surprises at deploy time."

### 4. Walk through Bicep modules (3 minutes)

Open `infra/main.bicep`:

> **Say:**
> "The infra is modular. `main.bicep` is the orchestrator — it calls three modules."

Open each module briefly:

**`infra/modules/fabric-capacity.bicep`**
> "Fabric capacity — F2 by default. The SKU is parameterized so you can scale up to F64 for production. Supports pause/resume for cost management."

**`infra/modules/keyvault.bicep`**
> "Key Vault for secrets — connection strings, API keys. The agents pull secrets from here at runtime, never from environment variables or code."

**`infra/modules/entra-app.bicep`**
> "Entra ID app registration for auth. This is the identity the agents use. Interactive auth for CLI, managed identity for Foundry, OIDC for CI/CD."

### 5. Auth model (1 minute)

> **Say:**
> "Auth is split by surface:
> - **CLI** — interactive browser login, token cached locally
> - **Foundry** — managed identity, no secrets in code
> - **CI/CD** — OIDC federation with GitHub Actions, no stored credentials
> - **M365** — bot registration via Entra app
>
> The principle: no long-lived secrets. Everything uses token-based auth with automatic rotation."

---

## Section 3 — Sub-Agent Walkthrough (6 minutes)

### 6. Pick the Researcher Agent (4 minutes)

Open `src/agents/researcher/mcp_server.py`:

> **Say:**
> "Let's look at one sub-agent end to end. The Researcher Agent does web search for customer intelligence. Here's the MCP server — it registers tools that any MCP client can discover and call."

Point out:
- Tool registration (function decorators or schema definitions)
- Input/output schemas
- How the server starts and listens

Open `src/agents/researcher/tools.py`:

> **Say:**
> "The tools module has the actual business logic. Each tool is a function that takes structured input, calls an external API, and returns structured output with citations. The MCP server is just the transport layer — the logic lives here."

Point out:
- Search function(s)
- Citation formatting
- Error handling

### 7. Run a unit test (2 minutes)

```bash
make test
```

Or run a specific test file:

```bash
pytest tests/unit/ -v -k "researcher"
```

> **Say:**
> "Unit tests mock external APIs — no network calls, no Fabric connection needed. They run in seconds. We test that tool inputs are validated, outputs match the expected schema, and error cases are handled."

Show the test output — highlight pass count and speed.

---

## Section 4 — MCP Integration (3 minutes)

### 8. Show MCP config (1.5 minutes)

Open `.copilot/mcp-config.json` (or the project's MCP config):

> **Say:**
> "This is how VS Code and the CLI discover our agents. Standard MCP configuration — each server gets a name, a command to start it, and optional environment variables. Add a new server here, restart Copilot, and it appears as a tool."

```json
{
  "servers": {
    "fabric-data-agent": { "...": "Fabric's built-in MCP endpoint" },
    "researcher": { "command": "python", "args": ["-m", "src.agents.researcher.mcp_server"] },
    "sharepoint": { "command": "python", "args": ["-m", "src.agents.sharepoint.mcp_server"] }
  }
}
```

### 9. Explain MCP discovery (1.5 minutes)

> **Say:**
> "MCP is a protocol, not a platform. The key concept:
> 1. **Client** (VS Code, CLI, Foundry) reads the config and starts the servers.
> 2. **Server** advertises its tools — name, description, input schema.
> 3. **Client** calls tools as needed during a conversation.
> 4. **No central registry** — it's all config-driven and local.
>
> This means you can test agents standalone, swap them out, or add new ones without touching the orchestrator."

---

## Section 5 — Report Generator (3 minutes)

### 10. Show templates (1.5 minutes)

Open `src/agents/report_generator/templates/`:

> **Say:**
> "Reports are template-based, not free-form LLM output. The template defines the structure — sections, formatting, citation style, branding. The generator fills it with data from the sub-agents."

Show a template file — point out:
- Section headers / placeholders
- Citation formatting
- Consistent structure

### 11. Explain citations (1.5 minutes)

Open `src/agents/report_generator/generator.py`:

> **Say:**
> "Every claim in a generated report includes a citation. The citation links back to the source: a Fabric query result, a web article URL, or a SharePoint document path.
>
> This is implemented at the template level — the generator inserts citations as footnotes or inline references. It's not an LLM afterthought. The template enforces it."

Show a generated DOCX if available (from `demo/sample-data/` or a pre-generated file):

> "Here's an example. See the footnotes? Each one traces back to a source. Click it and you get the Fabric query, the URL, or the SharePoint path."

---

## Section 6 — Eval Harness (3 minutes)

### 12. Run the eval (2 minutes)

```bash
make test-eval
```

Or with mock mode if no live Fabric connection:

```bash
python tests/eval/run_eval.py --mock
```

> **Say:**
> "The eval harness scores agent outputs against golden Q&A pairs. For example:
> - Question: 'Who are our top 5 customers by revenue?'
> - Golden answer: Tailspin Toys, Wingtip Toys, Contoso Ltd, ...
> - Agent answer: (whatever the agent returns)
> - Score: semantic similarity + factual accuracy
>
> This catches regressions when you change prompts, swap models, or modify tool logic."

Show the eval output — highlight scores and any failures.

### 13. Explain eval design (1 minute)

> **Say:**
> "The eval suite has three dimensions:
> 1. **Factual accuracy** — did the agent return correct data?
> 2. **Citation coverage** — did every claim have a source?
> 3. **Latency** — how long did the full pipeline take?
>
> We run this in CI on every PR. If accuracy drops below the threshold, the PR is blocked."

---

## Section 7 — Extensibility (4 minutes)

### 14. How to add a new sub-agent (2 minutes)

> **Say:**
> "Adding a new agent takes three steps:"

Walk through on screen (don't actually create files — just describe):

> "**Step 1:** Create a new directory under `src/agents/`. For example, `src/agents/crm/` for a CRM integration.
>
> **Step 2:** Implement two files:
> - `mcp_server.py` — registers tools, starts the MCP server
> - `tools.py` — business logic, API calls, citation formatting
>
> **Step 3:** Register it in `mcp-config.json`:
> ```json
> \"crm\": { \"command\": \"python\", \"args\": [\"-m\", \"src.agents.crm.mcp_server\"] }
> ```
>
> That's it. Restart Copilot and the new agent is available. No orchestrator changes needed — MCP handles discovery."

### 15. How to add a new surface (2 minutes)

> **Say:**
> "Adding a new consumption surface depends on which one:"

Point to `docs/surfaces/README.md`:

> "**M365 Direct** — portal-only. Publish the Fabric Data Agent from the Fabric UI. No code.
>
> **Copilot Studio** — low-code. Create a new agent in Studio, add the Fabric Data Agent as a connected agent, wire up connectors. No code in this repo.
>
> **Azure AI Foundry** — pro-code. The orchestrator in `src/orchestrator/` uses the Python SDK. You register tools, add FabricTool, and publish via the Foundry portal. This gives you the full pipeline including report generation.
>
> **CLI** — already here. The MCP config in this repo IS the CLI surface.
>
> The key insight: the sub-agents don't change. Only the surface layer changes."

---

## Section 8 — Cost Model & Wrap-up (2 minutes)

### 16. Show costs (1 minute)

Open `docs/costs.md`:

> **Say:**
> "Let's talk money. The biggest cost is Fabric capacity. F2 is ~$262/month. If your tenant requires F64 for Data Agent, that's ~$8,400/month. Everything else — Foundry, Key Vault, OpenAI — is negligible at demo scale.
>
> The critical cost management practice: **pause Fabric capacity when you're not using it.** Nights, weekends, between demos. `make infra-teardown` suspends the capacity, `make infra-resume` brings it back. That alone can save 70% on Fabric costs."

### 17. Wrap-up (1 minute)

> **Say:**
> "To summarize what we've walked through:
>
> | Layer | What you saw |
> |---|---|
> | **IaC** | Modular Bicep, parameterized, validate-before-deploy |
> | **Sub-agents** | MCP servers with clean separation of transport and logic |
> | **MCP integration** | Config-driven discovery, no central registry |
> | **Report generation** | Template-based with first-class citations |
> | **Eval harness** | Golden Q&A scoring, regression detection, CI-integrated |
> | **Extensibility** | New agent = 2 files + 1 config entry. New surface = pick your complexity. |
> | **Cost management** | Pause/resume Fabric capacity, budget alerts, tier selection |
>
> **Fork this repo, swap in your data, deploy in a day.** The accelerator gives you the scaffolding — you bring the data and the domain knowledge."

---

## If things go wrong

| Problem | Recovery |
|---|---|
| `make lint` fails | "Looks like there's a style issue — let me fix it live." Run `make format` then `make lint` again. |
| `make test` fails | Check error output. If it's a missing dependency: `pip install -r requirements.txt`. If it's a flaky test, skip it: `pytest tests/unit/ -v -k "not flaky_test"`. |
| `make infra-validate` fails | "Bicep validation requires Azure CLI to be authenticated. Let me check..." Run `az account show`. If not logged in: `az login`. |
| Eval scores are low | "The eval uses semantic similarity — scores vary by model. What matters is the trend: are scores improving or regressing across PRs?" |
| Live Fabric query fails | Switch to mock mode: `python tests/eval/run_eval.py --mock`. "Mock mode uses cached responses so we can demo without a live Fabric connection." |

---

## Key messages to land

1. **Production-ready scaffolding** — not a toy. IaC, testing, CI, auth, cost management.
2. **MCP is the integration layer** — open protocol, no vendor lock-in, config-driven.
3. **Three test tiers** — unit (fast, mocked), integration (MCP protocol), eval (LLM quality).
4. **Citations are structural** — enforced by templates, not LLM behavior.
5. **Extensibility is cheap** — new agent = 2 files + 1 config line. No framework to learn.
6. **Cost is manageable** — pause/resume, tier selection, budget alerts.
7. **Fork and go** — swap the data, keep the scaffolding, deploy in a day.
