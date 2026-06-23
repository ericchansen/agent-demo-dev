# Security Model (Demo)

> This is a **demo environment**. Production hardening (network isolation, RBAC, DLP policies) is disabled by default for ease of setup. See `infra/main.bicep` parameters to enable.

## Authentication Modes

| Mode | Surface | Details |
|------|---------|---------|
| Interactive (Entra ID) | CLI, VS Code | User signs in; delegated tokens flow to downstream services |
| Managed Identity | Foundry runtime | System-assigned MI on the Foundry project |
| Bot Registration | M365/Teams | Bot app reg handles OAuth for channel delivery |
| OIDC Federation | GitHub Actions | Workload identity — no stored secrets |

## Data Protection

- **Fabric Data Agent** enforces row-level security at the lakehouse layer
- **No customer data in this repo** — all data is sample/synthetic
- External calls (market research) send only company names and search queries
- Generated reports are ephemeral (local files or OneDrive upload)

## What's Disabled for Demo

| Control | Production Default | Demo Default | Re-enable |
|---------|-------------------|--------------|-----------|
| Network isolation | Private endpoints | Public access | Set `publicNetworkAccess=Disabled` in Bicep |
| Azure Policy | Deny non-compliant | No policy | Deploy policy assignments separately |
| RBAC lock-down | Least privilege | Contributor | Scope role assignments in `infra/modules/` |
| Key Vault soft-delete | Enabled | Enabled | Already on (required by Azure) |