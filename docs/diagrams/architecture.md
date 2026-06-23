# Architecture

```mermaid
graph TB
    subgraph surfaces["User Surfaces"]
        CLI["Copilot CLI<br/>MCP tools · Developer/SE"]
        M365["M365 Copilot Chat<br/>Agent card · Business users"]
        TEAMS["Teams Channel<br/>Agent card · Business users"]
        STUDIO["Copilot Studio<br/>Low-code · Citizen devs"]
        PORTAL["Foundry Portal<br/>Playground · Testing/Admin"]
    end

    subgraph orchestration["Sales Intelligence Workflow"]
        direction LR
        ORCH["Orchestrator<br/>Plan → Gather → Synthesize → Generate"]
    end

    subgraph data["Data Sources"]
        subgraph internal["Internal Data"]
            FABRIC["Fabric Data Agent<br/>SEC EDGAR financials<br/>Sales pipeline · Territory"]
            WORKIQ["WorkIQ / M365<br/>Emails · Meetings<br/>Engagement signals"]
        end
        subgraph external["External Data"]
            MR["Market Research Agent<br/>yfinance · Bing Grounding<br/>Analyst forecasts"]
        end
    end

    subgraph artifacts["Generated Artifacts"]
        direction LR
        XLSX["📊 Excel<br/>Quota estimates"]
        DOCX["📄 Word<br/>Account plans"]
        PDF["📋 PDF/HTML<br/>Executive summary"]
    end

    CLI --> ORCH
    M365 --> ORCH
    TEAMS --> ORCH
    STUDIO --> ORCH
    PORTAL --> ORCH

    ORCH --> FABRIC
    ORCH --> MR
    ORCH --> WORKIQ

    ORCH --> XLSX
    ORCH --> DOCX
    ORCH --> PDF
```

## Surfaces

| Surface | Audience | Topology | Repo |
|---------|----------|----------|------|
| **Copilot CLI** | Developers, SEs | 1 agent + MCP tools | `agent-demo-dev` |
| **M365 Copilot Chat** | Business users | Foundry agent → FabricIQ + WorkIQ | `agent-demo-dev` |
| **Teams** | Business users | Same Foundry agent, Teams channel | `agent-demo-dev` |
| **Copilot Studio** | Citizen devs | Low-code topics + connectors | Studio designer |
| **Foundry Portal** | Testing / admin | Playground chat UI | `agent-demo-dev` |

## Data Sources

| Source | What | Location |
|--------|------|----------|
| **Fabric Data Agent** | SEC EDGAR financials (~50 companies), sales pipeline, territory | OneLake Lakehouse |
| **Market Research Agent** | yfinance real-time data, Bing Grounding (news, forecasts) | `ericchansen/market-research` (separate deploy) |
| **WorkIQ / M365** | Emails, meetings, engagement signals | M365 Graph (mocked in demo) |

## Key Insight

The **workflow** is constant: gather internal data → gather external research → pull activity context → synthesize → generate artifacts.

The **surface** determines the deployment topology:
- CLI = one process with tool calls
- Foundry/M365/Teams = hosted agent with platform tools
- Copilot Studio = visual topic flows calling the same backends

"Multi-agent" isn't an architecture choice — it's a description of the workflow complexity.
