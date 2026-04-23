# Infrastructure — Fabric Sales Agent Accelerator

Bicep templates that provision the Azure resources needed by the accelerator.

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| **Azure CLI** | 2.61+ | `winget install Microsoft.AzureCLI` |
| **Bicep CLI** | 0.28+ | Ships with Azure CLI or `az bicep install` |
| **Azure subscription** | — | With permission to create resources and Entra app registrations |

## Authentication Model

The accelerator supports **four** identity patterns — pick the ones you need.

| Pattern | When to use | Identity type |
|---------|------------|---------------|
| **Interactive / delegated** | CLI or VS Code development against Fabric APIs | User signs in via `az login`; tokens carry the user's identity and permissions |
| **Managed identity** | Foundry runtime (Azure-hosted agent) calling Fabric or Key Vault | System-assigned managed identity on the compute resource; no secrets to manage |
| **OIDC federated credential** | GitHub Actions CI/CD deploying to Azure | Workload identity federation — GitHub's OIDC token is exchanged for an Azure token; no long-lived secrets stored in GitHub |
| **Bot app registration** | Publishing the agent to the M365 Copilot / Teams channel | Entra app with client ID + secret; required by the Bot Framework for channel auth |

> **Tip:** For local development you typically only need *interactive / delegated*.
> Add the other identities as you move toward CI/CD and production.

## Fabric Capacity SKU Notes

The **F2** SKU is the **minimum** tier that supports Fabric Data Agent features.

| SKU | CUs | Approx. monthly cost (USD) |
|-----|-----|---------------------------|
| F2 | 2 | ~$262 |
| F4 | 4 | ~$524 |
| F8 | 8 | ~$1,048 |
| F16 | 16 | ~$2,096 |

> Costs are estimates based on East US pay-as-you-go pricing.
> See [Microsoft Fabric pricing](https://azure.microsoft.com/pricing/details/microsoft-fabric/) for current rates.

**Cost-saving tip:** Pause or delete the capacity when you aren't using it (see *Teardown* below).

## Deploy

```bash
# 1. Log in and set the target subscription
az login
az account set --subscription "<subscription-id>"

# 2. Create a resource group (if it doesn't exist)
az group create --name rg-fsa-demo --location eastus

# 3. Deploy with the dev parameter file
az deployment group create \
  --resource-group rg-fsa-demo \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam \
  --parameters fabricAdminUpn='admin@contoso.com'
```

> `fabricAdminUpn` is passed on the command line so it doesn't need to live in source control.

### Entra ID App Registration (manual step)

Bicep cannot create Entra app registrations. After the deployment above, run the
CLI commands documented in [`infra/modules/entra-app.bicep`](modules/entra-app.bicep).

## Teardown / Cost Management

Fabric capacity bills continuously while it's running. To avoid unnecessary charges:

```bash
# Option 1 — Pause the capacity (preserves config, stops billing)
az fabric capacity suspend \
  --resource-group rg-fsa-demo \
  --capacity-name fsa-demo-capacity

# Option 2 — Resume when you need it again
az fabric capacity resume \
  --resource-group rg-fsa-demo \
  --capacity-name fsa-demo-capacity

# Option 3 — Delete the entire resource group (irreversible)
az group delete --name rg-fsa-demo --yes --no-wait
```

## File Structure

```
infra/
├── main.bicep                  # Top-level orchestration
├── parameters/
│   └── dev.bicepparam          # Dev / demo parameter values
├── modules/
│   ├── fabric-capacity.bicep   # Microsoft.Fabric/capacities
│   ├── keyvault.bicep          # Microsoft.KeyVault/vaults
│   └── entra-app.bicep         # Placeholder + CLI instructions
└── README.md                   # ← You are here
```
