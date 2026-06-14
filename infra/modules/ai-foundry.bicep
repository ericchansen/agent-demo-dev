// ---------------------------------------------------------------------------
// ai-foundry.bicep — Azure AI Foundry Hub (MachineLearningServices workspace)
//
// Security posture enforced:
//   • systemDatastoresAuthMode = identity  → default datastores use managed
//     identity (Entra) instead of access keys
//   • System-assigned managed identity enabled on the hub
//   • publicNetworkAccess defaults to Disabled
//   • RBAC: Storage Blob Data Contributor auto-assigned to hub MI on the
//     linked storage account (no manual step required)
//
// Note: The CogSvcs project (fsa-hub-2026/fsa-project) is a child resource
// of the AI Services account, NOT an MLS workspace. It inherits security
// settings from its parent and is managed via the cognitive-services module.
// ---------------------------------------------------------------------------

@description('Name of the AI Foundry Hub (MachineLearningServices workspace).')
param hubName string

@description('Azure region.')
param location string

@description('Resource ID of the linked Key Vault.')
param keyVaultId string

@description('Resource ID of the linked Storage account.')
param storageAccountId string

@description('Resource tags.')
param tags object = {}

@description('Public network access for the AI Foundry hub.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Disabled'

@description('Optional role assignment resource name when the storage RBAC assignment already exists.')
param storageRoleAssignmentName string = ''

// ── Storage account reference (for scoping the RBAC assignment) ─────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: last(split(storageAccountId, '/'))
}

// ── AI Foundry Hub ──────────────────────────────────────────────────────────
resource hub 'Microsoft.MachineLearningServices/workspaces@2025-06-01' = {
  name: hubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    keyVault: keyVaultId
    storageAccount: storageAccountId
    publicNetworkAccess: publicNetworkAccess
    #disable-next-line BCP037
    networkAcls: {
      defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
      ipRules: []
      resourceAccessRules: []
    }
    // Set default datastore connections to use the hub's managed identity instead of access keys.
    systemDatastoresAuthMode: 'identity'
  }
}

// ── RBAC: Grant hub MI "Storage Blob Data Contributor" on linked storage ────
// This eliminates the need for a manual role assignment before flipping
// systemDatastoresAuthMode from 'accesskey' to 'identity'.
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource hubStorageRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: empty(storageRoleAssignmentName) ? guid(storageAccount.id, hub.id, storageBlobDataContributorRoleId) : storageRoleAssignmentName
  scope: storageAccount
  properties: {
    principalId: hub.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleId
    )
  }
}

@description('Resource ID of the Foundry Hub.')
output hubId string = hub.id

@description('Principal ID of the hub system-assigned managed identity.')
output hubPrincipalId string = hub.identity.principalId
