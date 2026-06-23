# Architecture Overview

> **Canonical diagram and surface matrix:** See [`docs/diagrams/architecture.md`](diagrams/architecture.md)

This repo implements a **sales intelligence workflow** that queries internal CRM/sales data (via Microsoft Fabric Data Agent or Databricks Genie) and external market data (via a separate [market-research](https://github.com/ericchansen/market-research) service), then synthesizes findings into cited reports.

## Delivery Surfaces

The same workflow is accessible through five surfaces:

| Surface | Auth Model | Best For |
|---------|-----------|----------|
| **GitHub Copilot CLI** | Interactive (Entra ID) | Rapid prototyping, developer iteration |
| **M365 Copilot** | Delegated (OBO) | End-user production experience |
| **Microsoft Teams** | Bot registration | Channel-based team collaboration |
| **Copilot Studio** | Connector auth | Low-code customization, citizen devs |
| **Azure AI Foundry Portal** | Managed identity | Testing, monitoring, tracing |

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Foundry Agent | `src/orchestrator/` | Agent definition, tool schemas, instruction builder |
| Quota Estimator | `src/agents/quota_estimator/` | Territory/quota analysis pipeline |
| CLI Skills | `src/cli/skills/` | MCP skill definitions for Copilot CLI |
| Infrastructure | `infra/` | Bicep IaC for all Azure resources |
| Fabric Config | `fabric/` | Data Agent instructions and few-shot examples |

| Surface | Description | Status |
|---------|-------------|--------|
| **GitHub Copilot CLI** | Full multi-agent workflow via MCP tool calls in your terminal. Skill-based orchestration chains Fabric, research, and WorkIQ into artifacts (Excel, HTML, DOCX). | ✅ Implemented |
