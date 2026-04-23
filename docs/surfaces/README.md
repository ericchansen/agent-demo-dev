# Choose Your Architecture

This repo demonstrates four surfaces for exposing a Fabric-backed sales agent to end users. Each surface trades off simplicity for capability — pick the one that fits your team.

---

## Comparison Table

| Feature | GitHub Copilot (CLI / VS Code) | M365 Copilot (Direct) | Copilot Studio | Azure AI Foundry |
|---|---|---|---|---|
| **Audience** | Developers, data engineers | Business users (M365) | Business users (M365 / Teams) | Developers + business users |
| **Code required** | CLI commands only | None (zero-code) | Low-code (visual designer) | Python SDK (pro-code) |
| **Fabric data queries** | ✅ via CLI tool | ✅ NL→SQL | ✅ via connected agent | ✅ via FabricTool |
| **Web research** | ✅ custom function | ❌ | ✅ via Bing connector | ✅ custom function |
| **SharePoint access** | ✅ custom function | ❌ | ✅ via connector | ✅ custom function |
| **Report generation (DOCX/PPTX)** | ✅ custom function | ❌ | ❌ | ✅ custom function |
| **M365 Copilot Chat** | ❌ | ✅ | ✅ | ✅ (via publish) |
| **Teams** | ❌ | ❌ | ✅ | ✅ (via Bot Framework) |
| **Multi-agent orchestration** | ❌ | ❌ | ⚠️ Limited | ✅ Full |
| **Setup effort** | ~10 min | ~30 min | ~2 hours | ~1 day |
| **Licensing cost** | GitHub Copilot | Fabric + M365 Copilot | Fabric + M365 Copilot + Copilot Studio | Fabric + Azure sub + M365 Copilot |

### Legend

- ✅ = Fully supported
- ⚠️ = Partially supported / limited
- ❌ = Not supported

---

## When to Use Which

### 🖥️ GitHub Copilot (CLI / VS Code)

**Best for:** Developers and data engineers who live in the terminal or VS Code.

- Fastest to set up — just configure the MCP server and go.
- Full pipeline (data + research + reports) via CLI tool calls.
- Not suitable for business users who don't use developer tools.

→ See: `src/cli/` and `demo/` for the CLI agent implementation.

---

### 📋 M365 Copilot — Direct Fabric Publish

**Best for:** Quick demos and simple data Q&A with no code.

- Zero-code: publish from Fabric portal → appears in M365 Copilot Chat.
- Fabric data queries only — no web research, no SharePoint, no reports.
- Fastest path to putting a data agent in front of M365 users.

→ See: [`docs/surfaces/m365-direct.md`](m365-direct.md)

---

### 🧩 Copilot Studio (Low-Code)

**Best for:** Business users who want multi-source answers without writing code.

- Add Fabric Data Agent + SharePoint + web search connectors in a visual designer.
- Publish to M365 Copilot Chat and Teams.
- No report generation — answers are text-only.
- Good middle ground when Foundry is overkill but Direct Publish is too limited.

→ See: [`docs/surfaces/copilot-studio.md`](copilot-studio.md)

---

### 🔧 Azure AI Foundry (Pro-Code)

**Best for:** Production agents that need the full pipeline.

- Full Python SDK control: FabricTool + custom functions + multi-agent orchestration.
- Report generation (DOCX, PPTX) as downloadable files.
- Publish to M365 Copilot, Teams, custom web UI, or CLI.
- Most powerful — and most complex. Requires Azure subscription and Python development.

→ See: [`docs/surfaces/foundry.md`](foundry.md)

---

## Decision Flowchart

```
Do your users live in M365 Copilot Chat or Teams?
├── No → GitHub Copilot CLI (developer audience)
└── Yes
    ├── Do they only need Fabric data queries?
    │   ├── Yes → M365 Direct Publish (zero-code)
    │   └── No
    │       ├── Do they need report generation (DOCX/PPTX)?
    │       │   ├── Yes → Azure AI Foundry (pro-code)
    │       │   └── No
    │       │       ├── Do you have Python developers?
    │       │       │   ├── Yes → Azure AI Foundry (pro-code)
    │       │       │   └── No → Copilot Studio (low-code)
    │       └── Do they need custom orchestration logic?
    │           ├── Yes → Azure AI Foundry (pro-code)
    │           └── No → Copilot Studio (low-code)
```

---

## This Repo Demonstrates All Four

| Surface | Code Location |
|---|---|
| GitHub Copilot CLI | `src/cli/`, `demo/` |
| M365 Direct Publish | `docs/surfaces/m365-direct.md` (portal-only, no code) |
| Copilot Studio | `docs/surfaces/copilot-studio.md` (Studio UI, no code in repo) |
| Azure AI Foundry | `src/orchestrator/foundry_agent.py` |

Pick the one that fits your team — or combine them. The same Fabric Data Agent backs all four surfaces.
