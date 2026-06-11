// ---------------------------------------------------------------------------
// ai-foundry.bicep — Azure AI Foundry Hub + Project
//
// Security posture enforced:
//   • systemDatastoresAuthMode = identity  → default datastores use managed
//     identity (Entra) instead of access keys
//   • System-assigned managed identity enabled on the hub
//   • publicNetworkAccess = Disabled
//
// ⚠️  PREREQUISITE — one-time manual step before deploying:
//   The hub's system-assigned MI must have "Storage Blob Data Contributor"
//   on the linked storage account BEFORE flipping systemDatastoresAuthMode
//   from 'accesskey' to 'identity', or the workspace will lose access to
//   its default datastore.
//
//   az role assignment create \
//     --assignee-object-id <hub-mi-principalId> \
//     --assignee-principal-type ServicePrincipal \
//     --role "Storage Blob Data Contributor" \
//     --scope <storageAccountId>
// ---------------------------------------------------------------------------

@description('Name of the AI Foundry Hub (MachineLearningServices workspace).')
param hubName string

@description('Name of the AI Foundry Project inside the hub.')
param projectName string

@description('Azure region.')
param location string

@description('Resource ID of the linked Key Vault.')
param keyVaultId string

@description('Resource ID of the linked Storage account.')
param storageAccountId string

@description('Resource tags.')
param tags object = {}

resource hub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
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
    publicNetworkAccess: 'Disabled'
    // systemDatastoresAuthMode is not yet in the Bicep type library (BCP037 is a false-positive;
    // the property exists in the MachineLearningServices REST API and is accepted by ARM).
    // It sets default datastore connections to use the hub's managed identity instead of access keys.
    #disable-next-line BCP037
    systemDatastoresAuthMode: 'identity'
  }
}

resource project 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: projectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hubResourceId: hub.id
    publicNetworkAccess: 'Disabled'
    #disable-next-line BCP037
    systemDatastoresAuthMode: 'identity'
  }
}

@description('Resource ID of the Foundry Hub.')
output hubId string = hub.id

@description('Principal ID of the hub system-assigned managed identity.')
output hubPrincipalId string = hub.identity.principalId

@description('Resource ID of the Foundry Project.')
output projectId string = project.id
