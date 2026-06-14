---
sidebar_position: 1
title: System Overview
---

# System Overview

This page shows how all the pieces fit together — both delivery surfaces, shared backends, and the connections between them.

## Full system diagram

```mermaid
flowchart TB
    subgraph User["User Surfaces"]
        CLI["GitHub Copilot CLI\n(developer prototype)"]
        M365["M365 Copilot Chat / Teams\n(business users)"]
    end

    subgraph Orchestration["Orchestration Layer"]
        CopilotEngine["Copilot CLI Engine\n(built-in orchestrator)"]
        FoundryAgent["Azure AI Foundry\nAgent Service"]
    end

    subgraph Tools["Tool Layer"]
        MCP_FDA["wwi-sales-data\n(MCP server)"]
        MCP_WIQ["workiq\n(MCP server)"]
        Skills["Skills\n(prompt templates)"]
        FIQ["FabricIQPreviewTool\n(platform tool)"]
        WIQT["WorkIQPreviewTool\n(platform tool)"]
        ReportFunc["Report generator\n(function tool)"]
    end

    subgraph Backend["Shared Backend Services"]
        DA["Fabric Data Agent"]
        LH["Fabric Lakehouse\n(WWI: 6 tables)"]
        WIQ["WorkIQ\n(M365 Graph)"]
        OD["OneDrive\n(report storage)"]
    end

    CLI --> CopilotEngine
    M365 --> FoundryAgent

    CopilotEngine --> MCP_FDA
    CopilotEngine --> MCP_WIQ
    CopilotEngine --> Skills

    FoundryAgent --> FIQ
    FoundryAgent --> WIQT
    FoundryAgent --> ReportFunc

    MCP_FDA --> DA
    FIQ --> DA
    DA --> LH

    MCP_WIQ --> WIQ
    WIQT --> WIQ

    ReportFunc --> OD

    style CLI fill:#e8f4fd,stroke:#0078d4,stroke-width:2px
    style M365 fill:#f3e8fd,stroke:#5B4B8A,stroke-width:2px
    style DA fill:#fff3e0,stroke:#F57C00
    style LH fill:#fff3e0,stroke:#F57C00
```

## Data flow

1. **User asks a question** in either surface (CLI or M365 Copilot)
2. **Orchestrator selects tools** based on user intent — Copilot CLI engine or Foundry Responses API
3. **Fabric Data Agent** translates NL→SQL and queries the Lakehouse
4. **WorkIQ** retrieves M365 activity signals via OBO auth
5. **Report generator** (Foundry only) produces DOCX and uploads to OneDrive
6. **Response returned** to user with data, context, and deliverables

## Key design decisions

### Why two surfaces?
Different users need different experiences. Developers iterate faster in a terminal. Business users live in Teams and Outlook. Same agent logic, different distribution.

### Why MCP?
MCP standardizes tool discovery and calling. Write a tool server once, connect it to any MCP-compatible agent. The Fabric Data Agent already exposes an MCP endpoint — no custom wrapper needed.

### Why Foundry for production?
Foundry provides enterprise-grade agent hosting: Entra identity, RBAC, monitoring, and publishing to M365 — things that are hard to build yourself.

### Why not just one surface?
You *could* deploy only the Foundry surface. But the CLI surface gives you a zero-infrastructure prototyping environment. Changes to your MCP servers and skills take effect immediately — no deployment, no registration, no waiting. That feedback loop is critical during development.

## Further reading

- [Architecture: CLI surface](./cli-surface)
- [Architecture: Foundry surface](./foundry-surface)
- [Architecture: Auth patterns](./auth-patterns)
