// ---------------------------------------------------------------------------
// storage.bicep — Azure Storage Account for Fabric Sales Agent
//
// Security posture enforced:
//   • defaultToOAuthAuthentication = true  → UI and SDK default to Entra auth
//   • allowSharedKeyAccess = false          → shared-key (access-key) auth blocked
//   • minimumTlsVersion = TLS1_2            → no legacy TLS
//   • publicNetworkAccess = Disabled        → no direct internet exposure
// ---------------------------------------------------------------------------

@description('Name of the Storage account.')
param name string

@description('Azure region.')
param location string

@description('Storage SKU (LRS is sufficient for a demo; use GRS/ZRS for prod).')
@allowed(['Standard_LRS', 'Standard_GRS', 'Standard_ZRS', 'Premium_LRS'])
param sku string = 'Standard_LRS'

@description('Resource tags.')
param tags object = {}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: sku
  }
  properties: {
    // Entra ID (OAuth) as the default authentication experience in the portal and SDKs.
    defaultToOAuthAuthentication: true
    // Block all shared-key / SAS-key access; identity-based only.
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
  }
}

@description('Resource ID of the Storage account.')
output storageAccountId string = storageAccount.id

@description('Name of the Storage account.')
output storageAccountName string = storageAccount.name
