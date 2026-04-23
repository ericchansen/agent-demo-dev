// ---------------------------------------------------------------------------
// entra-app.bicep — Placeholder for Entra ID App Registration
// ---------------------------------------------------------------------------
//
// ⚠️  LIMITATION: Bicep / ARM cannot create Entra ID (Azure AD) app
// registrations. The Microsoft.Graph Bicep extension is in preview and not
// yet suitable for production use. Create the app registration manually or
// via the Azure CLI commands below.
//
// ── Step 1: Create the app registration ────────────────────────────────────
//
//   az ad app create --display-name "<entraAppName>" \
//     --sign-in-audience AzureADMyOrg
//
// ── Step 2: Create a service principal ─────────────────────────────────────
//
//   az ad sp create --id <appId>
//
// ── Step 3 (optional): Add OIDC federated credential for GitHub Actions ───
//
//   az ad app federated-credential create --id <appId> --parameters '{
//     "name": "github-actions-oidc",
//     "issuer": "https://token.actions.githubusercontent.com",
//     "subject": "repo:<org>/<repo>:ref:refs/heads/main",
//     "audiences": ["api://AzureADTokenExchange"]
//   }'
//
// ── Step 4 (optional): Add a client secret for local dev ───────────────────
//
//   az ad app credential reset --id <appId> --display-name "local-dev"
//
// ── Step 5: Store credentials in Key Vault ─────────────────────────────────
//
//   az keyvault secret set --vault-name <kvName> --name "EntraAppClientId" --value <appId>
//   az keyvault secret set --vault-name <kvName> --name "EntraAppClientSecret" --value <secret>
//
// ---------------------------------------------------------------------------

// This parameter exists so main.bicep can reference this module without error.
@description('Display name for the Entra ID app registration (informational only).')
param entraAppName string

// No resources are deployed — this file is documentation only.

@description('Reminder: create the Entra app registration manually (see comments above).')
output setupInstructions string = 'Run the az CLI commands in infra/modules/entra-app.bicep to create app "${entraAppName}".'
