# Agent Instructions (AGENTS.md)

## Autonomous Operation Mode

This repository is managed by an autonomous agent loop (Agent Looper). When running
in non-interactive mode (`copilot -p`), the following overrides apply:

- **Push directly** to main without user review or approval
- **Do NOT create PRs** -- commit and push directly to main
- **Do NOT ask for confirmation** -- make decisions autonomously
- **Commit frequently** with conventional commit messages
- **Run CI checks locally** before pushing (ruff, mypy, pytest, website build)
- **Use `az CLI`** freely to inspect and update Azure resources in rg-sales-agent-demo
- **Use `gh CLI`** to push, check workflows, etc.
- **Fix issues immediately** -- if tests fail, fix them before moving on
- **Never rewrite published git history** -- no force-push

## Native Foundry Agent Deployment

The workshop must show agents running INSIDE Azure AI Foundry, not just as local code:

- **Foundry Project (modern, account-based)**:
  * `sales-agent-demo-project` under AI Services account `salesagentdemoais`.
    Endpoint: `https://salesagentdemoais.services.ai.azure.com/api/projects/sales-agent-demo-project`.
    Create with `az cognitiveservices account project create` (needs `allowProjectManagement=true`).
    This is what `FOUNDRY_PROJECT_ENDPOINT` must point to.
- **Agent Registration**: Use the Azure AI Foundry SDK (`azure-ai-projects`) to register
  agents in the project. Verify with `scripts/verify_foundry_agent.py` — the agent
  (`SalesAgent`) is then visible in the Foundry portal playground. When `FABRIC_IQ_CONNECTION_ID`
  is unset, a demo-safe `fabric_query` function tool stands in for the Fabric IQ platform tool.
- **What to show in docs**:
  * Creating an agent in the Foundry portal UI (screenshots or step-by-step)
  * The same agent created via Python SDK (`azure-ai-projects`)
  * Testing in the Foundry playground
  * Monitoring/tracing agent runs in the portal
  * Publishing the agent to M365 Copilot and Teams channels. In the current Foundry
    Agent object model the stable endpoint, Entra identity, version, and agent card live
    on the Agent itself — there is no separate legacy application resource. Publishing
    now means exposing the agent through M365/Teams channels via its agent card. See
    [Migrate to the new Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/migrate).
- **Multi-agent pipelines**: Build a WORKING proof-of-concept. The exact architecture is
  aspirational -- use /research to discover what Foundry's SDK actually supports today for
  agent-to-agent communication, then build the best PoC that's actually achievable. Push
  back on this spec if the SDK doesn't support something -- adapt the design to reality.
  Starting point (adjust based on research):
  * Create `src/orchestrator/multi_agent/` with specialized agents:
    - Data Agent: queries Fabric Data Agent OR Databricks Genie for sales/business data
    - Research Agent: uses /research or web search for market trends, competitive intel
    - (Work Context Agent: WorkIQ for M365 activity -- mocked for now, real when available)
    - Conversational Agent: the "brain" that a user talks to. It has access to the data
      agent and research agent outputs. It can answer questions, provide analysis, and
      when the user asks for a report, it delegates to the Report Agent.
    - Report Agent: takes the combined context (data + research + work activity) and
      generates XLSX/HTML/PDF artifacts
  * Each agent should ideally be a separate Foundry agent registration (if SDK supports it)
  * Add tests that verify the pipeline end-to-end with mocked agent responses
  * The multi-agent pipeline should aim to produce the same outputs as the other surfaces
    (quota reports, sales analysis) -- showing THREE ways to achieve the same outcome:
    1. Copilot CLI (prototype, developer-facing)
    2. Single Foundry agent with tools (simple production path)
    3. Multi-agent pipeline (advanced, more observable, more composable)
    Workshop attendees should be able to compare all three side by side.
- **The hosted agent** in `src/orchestrator/hosted_agent/` should be deployable to the project
  as a managed compute endpoint, not just a local Docker container.
- **Never rewrite published git history** — no force-push on shared branches

## Workshop Experience Requirements

This is a 2-day hands-on workshop. The docs site and repo must deliver a "wow" experience:

**Visual / Interactive elements the docs site MUST have:**
- Architecture diagrams (Mermaid or SVG) on every architecture page -- not text-only
- Screenshots of the Foundry portal showing agents, playground, monitoring
- Screenshots of Copilot CLI in action (terminal output showing a query -> report flow)
- Screenshots of generated artifacts (Excel opened, HTML report in browser, PDF)
- An interactive "Try It Now" section with copy-paste commands that work immediately
- A cost calculator or cost table so attendees know what they're spending
- A troubleshooting page for common setup issues

**Demo flow that must be smooth and clickable:**
1. `git clone` -> `uv sync` -> `copilot` -> ask a question -> get a report (< 5 min)
2. Open Foundry portal -> see the agent -> test in playground -> see traces
3. Open the generated Excel/HTML/PDF artifacts and show real data
4. Show the Docusaurus site as the "how we built this" reference
5. Customize: change the data source, add a skill, regenerate

**Sample prompts / golden queries the docs should include:**
- "What were Tailspin Toys' total sales last quarter?"
- "Generate a quota estimation report for Northwest territory"
- "Compare conservative vs aggressive scenarios for FY27"
- "What's our pipeline coverage ratio by salesperson?"
- "Create a competitive analysis for Wingtip Toys"

**Things that KILL a demo (avoid at all costs):**
- Broken links in the docs site
- CLI commands that don't work when copy-pasted
- Azure resources that aren't accessible (network blocked, missing permissions)
- "Coming soon" or placeholder pages
- Import errors or missing dependencies
- Stale screenshots that don't match current UI

**Sales Agent Demo** is a reference implementation demonstrating how to combine Microsoft Fabric Data Agent with agentic AI workflows. It uses SEC EDGAR financial data for ~50 US public companies.

## Architecture

This demo is scoped to **five delivery surfaces** that share the same sales intelligence workflow and Fabric backend:

1. **GitHub Copilot CLI (prototype)** — MCP-based developer surface
   - `sales-data` for Fabric Data Agent queries
   - `workiq` for M365 activity context (**mocked in the demo tenant**)
   - `quota-forecast` skill for inline report output
2. **M365 Copilot + Teams (production path)** — Azure AI Foundry agent published to M365/Teams channels via its agent card (the stable endpoint and Entra identity live on the Agent object; the legacy application resource is being [retired](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/migrate))
   - `FabricIQPreviewTool` for Fabric-backed NL→SQL
   - `WorkIQPreviewTool` for M365 activity data in production
   - Custom function tools for report generation and business actions

**Copilot Studio** and **M365 Direct Publish** are documented in `docs/surfaces/` but not implemented in this demo.

## Coding Standards

- **Language:** Python 3.11+
- **Linting:** Ruff (rules: E, F, I, N, W, UP). Line length 120.
- **Type checking:** mypy strict for `src/agents/`, lenient for integration code
- **Testing:** pytest. Unit tests mock external services. Integration tests verify MCP protocol.
- **Formatting:** Ruff formatter
- **IaC:** Bicep (Azure-native). Modules in `infra/modules/`.
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `infra:`, `test:`)

## CI Checks

CI runs on every PR to `main`. Run these locally before pushing:

```bash
uv sync --extra dev                # install project + dev tools (or: pip install -e ".[dev]")
ruff check .                       # lint
ruff format --check .              # formatting (run `ruff format .` to auto-fix)
mypy src/                          # type checking
pytest tests/unit/                 # unit tests
```

All four must pass. The Bicep template is also validated (`az bicep build --file infra/main.bicep`).

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | Local MCP servers, demo mocks, and report generation helpers |
| `src/orchestrator/` | Azure AI Foundry agent and tool wiring for the M365 / Teams surface |
| `src/cli/` | Copilot CLI MCP config and skills for the prototype surface |
| `infra/` | Bicep IaC (Fabric capacity, Key Vault, Entra app, Foundry) |
| `fabric/` | Fabric Data Agent config, instructions, few-shot examples |
| `demo/` | Demo scripts and sample data |
| `docs/` | Architecture, security, setup, and two-surface guidance |
| `docs/surfaces/` | Reference-only documentation for additional surfaces |
| `tests/` | Unit, integration, and eval tests |

## Important Notes

- **LLM-agnostic** — never hardcode a model provider. Config accepts any endpoint.
- **Citations first-class** — every generated report must include source attribution.
- **Fabric MCP is built-in** — use the Data Agent's native MCP server, not a custom wrapper.
- **Auth split** — interactive for CLI, managed identity for Foundry, OIDC for CI, bot reg for M365.
- **WorkIQ demo mode** — production targets WorkIQ / OBO flows; the demo tenant uses mock M365 activity data until provisioning is available.
- **No customer data in repo** — all data is SEC EDGAR public filings and synthetic sales fixtures.
