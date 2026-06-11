// ---------------------------------------------------------------------------
// keyvault.bicep — Azure Key Vault (RBAC-managed, no inline access policies)
// ---------------------------------------------------------------------------

@description('Name of the Key Vault.')
param name string

@description('Azure region.')
param location string

@description('Resource tags.')
param tags object = {}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    accessPolicies: [] // Managed entirely via Azure RBAC — no inline policies
  }
}

@description('URI of the Key Vault (e.g. https://<name>.vault.azure.net/).')
output vaultUri string = vault.properties.vaultUri

@description('Resource ID of the Key Vault.')
output keyVaultId string = vault.id
