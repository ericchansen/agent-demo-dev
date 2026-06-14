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
        Cowork["Cowork\n(M365 plugin)"]
    end

    subgraph Orchestration["Orchestration Layer"]
        CopilotEngine["Copilot CLI Engine\n(built-in orchestrator)"]
        FoundryPrompt["Foundry Prompt Agent\n(declarative)"]
        FoundryHosted["Foundry Hosted Agent\n(bring-your-own-code)"]
    end

    subgraph Tools["Tool Layer"]
        FDA["Fabric Data Agent\n(MCP)"]
        WIQ["WorkIQ\n(MCP)"]
        Researcher["Researcher Agent\n(web search MCP)"]
        SharePoint["SharePoint Agent\n(Graph MCP)"]
        Skills["Skills\n(prompt templates)"]
        FIQ["FabricIQPreviewTool"]
        WIQT["WorkIQPreviewTool"]
        ReportFunc["Report generator\n(function tool)"]
    end

    subgraph Backend["Shared Backend Services"]
        DA_WWI["Fabric Data Agent\n(WWI Lakehouse)"]
        DA_MKT["Fabric Data Agent\n(Market Data Lakehouse)"]
        Graph["M365 Graph\n(WorkIQ + SharePoint)"]
        OD["OneDrive\n(report storage)"]
    end

    CLI --> CopilotEngine
    M365 --> FoundryPrompt
    M365 --> FoundryHosted
    Cowork --> CopilotEngine

    CopilotEngine --> FDA
    CopilotEngine --> WIQ
    CopilotEngine --> Researcher
    CopilotEngine --> SharePoint
    CopilotEngine --> Skills

    FoundryPrompt --> FIQ
    FoundryPrompt --> WIQT
    FoundryPrompt --> ReportFunc

    FoundryHosted --> FIQ
    FoundryHosted --> ReportFunc

    FDA --> DA_WWI
    FDA --> DA_MKT
    FIQ --> DA_WWI

    WIQ --> Graph
    WIQT --> Graph
    SharePoint --> Graph
    Researcher -.->|web search| Web["External APIs"]

    ReportFunc --> OD

    style CLI fill:#e8f4fd,stroke:#0078d4,stroke-width:2px
    style M365 fill:#f3e8fd,stroke:#5B4B8A,stroke-width:2px
    style Cowork fill:#f3e8fd,stroke:#5B4B8A,stroke-width:2px
    style DA_WWI fill:#fff3e0,stroke:#F57C00
    style DA_MKT fill:#fff3e0,stroke:#F57C00
```

## Data flow

1. **User asks a question** in any surface (CLI, M365 Copilot, or Cowork)
2. **Orchestrator selects tools** based on user intent — Copilot CLI engine, Foundry Prompt Agent, or Foundry Hosted Agent
3. **Fabric Data Agent** translates NL→SQL and queries the Lakehouse (WWI sales data or market/SEC data)
4. **WorkIQ** retrieves M365 activity signals via OBO auth
5. **Researcher Agent** performs web research with configurable search providers (Bing, Tavily, or mock)
6. **SharePoint Agent** retrieves internal documents via Microsoft Graph
7. **Report generator** (Foundry) produces DOCX/PPTX and uploads to OneDrive
8. **Response returned** to user with data, context, and deliverables

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
