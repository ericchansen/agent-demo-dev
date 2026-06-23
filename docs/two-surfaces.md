# Delivery Surfaces

This demo delivers the same sales intelligence workflow through five surfaces.
Each represents a different deployment model — from rapid prototyping to managed production.

## Surface Matrix

| Surface | Auth | Data Access | Report Delivery | Status |
|---------|------|-------------|-----------------|--------|
| **Copilot CLI** | Interactive Entra ID | MCP servers (Fabric, WorkIQ) | Inline markdown / XLSX / HTML | ✅ Working |
| **M365 Copilot** | Delegated (OBO) | FabricIQ + WorkIQ platform tools | Adaptive cards, file links | ✅ Publishable |
| **Microsoft Teams** | Bot registration | Same as M365 Copilot (channel) | Adaptive cards in channel | ✅ Publishable |
| **Copilot Studio** | Connector auth | Fabric connector + custom actions | Cards, Power Automate flows | 📋 Documented |
| **Foundry Portal** | Managed identity | Direct SDK calls | Playground / trace viewer | ✅ Working |

## Prototype → Production Path

`
CLI (prototype) → Foundry (test/trace) → M365/Teams (production)
                                       → Copilot Studio (citizen dev)
`

1. **Prototype in CLI** — Fast iteration on prompts, tool schemas, data quality
2. **Test in Foundry Portal** — Verify agent registration, inspect traces, tune instructions
3. **Publish to M365/Teams** — Production experience for end users via Foundry publish flow
4. **Extend in Copilot Studio** — Low-code customization for business users

## Capability Translation

| Capability | CLI (MCP) | Foundry/M365 (Platform Tools) |
|---|---|---|
| Sales data | `sales-data` MCP server | `FabricIQPreviewTool` |
| Market research | `market-research` external service | Custom function tool |
| M365 activity | `workiq` MCP server | `WorkIQPreviewTool` |
| Report generation | `quota-forecast` skill | Custom function tool → DOCX |