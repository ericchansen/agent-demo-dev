// ---------------------------------------------------------------------------
// main.bicep — Top-level orchestration for Fabric Sales Agent Accelerator
// ---------------------------------------------------------------------------

targetScope = 'resourceGroup'

// ── Parameters ──────────────────────────────────────────────────────────────

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('SKU for the Microsoft Fabric capacity (F2 is minimum for Data Agent).')
@allowed(['F2', 'F4', 'F8', 'F16', 'F32', 'F64', 'F128', 'F256', 'F512', 'F1024', 'F2048'])
param fabricCapacitySku string = 'F2'

@description('Name of the Microsoft Fabric capacity resource.')
param fabricCapacityName string

@description('Name of the Azure Key Vault.')
param keyVaultName string

@description('Display name for the Entra ID app registration (created out-of-band).')
param entraAppName string

@description('UPN of the Fabric capacity administrator (e.g. admin@contoso.com).')
param fabricAdminUpn string = ''

@description('Name of the Azure Storage account used by AI Foundry.')
param storageAccountName string

@description('Name of the primary Cognitive Services / AI Services account (fabricagentai2026).')
param cogServicesName string

@description('Name of the AI Foundry Hub Cognitive Services account (fsa-hub-2026).')
param foundryHubCogServicesName string

@description('Name of the AI Foundry Hub workspace (fabric-agent-hub).')
param foundryHubName string

@description('Public network access for demo-facing resources. Keep Disabled for production; dev can override to Enabled for portal access.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Disabled'

@description('Optional existing role assignment name for the Foundry hub managed identity on storage. Use only to make redeploys idempotent when the assignment already exists with a non-default name.')
param foundryHubStorageRoleAssignmentName string = ''

@description('Optional resource ID of an external (management-group) policy assignment whose "modify" effect forces Foundry hubs to publicNetworkAccess=Disabled. When set, a Waiver exemption is created so the dev hub stays reachable. Leave empty in production.')
param foundryHubPnaExemptionAssignmentId string = ''

@description('Resource tags applied to every resource.')
param tags object = {}

// ── Modules ─────────────────────────────────────────────────────────────────

module fabricCapacity './modules/fabric-capacity.bicep' = {
  name: 'fabricCapacity'
  params: {
    name: fabricCapacityName
    location: location
    sku: fabricCapacitySku
    adminMemberUpn: fabricAdminUpn
    tags: tags
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tags: tags
  }
}

module storage './modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: storageAccountName
    location: location
    publicNetworkAccess: publicNetworkAccess
    tags: tags
  }
}

module cogServices './modules/cognitive-services.bicep' = {
  name: 'cogServices'
  params: {
    name: cogServicesName
    location: location
    customSubDomainName: cogServicesName
    publicNetworkAccess: publicNetworkAccess
    tags: tags
  }
}

module foundryHubCogServices './modules/cognitive-services.bicep' = {
  name: 'foundryHubCogServices'
  params: {
    name: foundryHubCogServicesName
    location: location
    customSubDomainName: foundryHubCogServicesName
    publicNetworkAccess: publicNetworkAccess
    tags: tags
  }
}

module aiFoundry './modules/ai-foundry.bicep' = {
  name: 'aiFoundry'
  params: {
    hubName: foundryHubName
    location: location
    keyVaultId: keyVault.outputs.keyVaultId
    storageAccountId: storage.outputs.storageAccountId
    publicNetworkAccess: publicNetworkAccess
    storageRoleAssignmentName: foundryHubStorageRoleAssignmentName
    tags: tags
  }
}

module policies './modules/policy.bicep' = {
  name: 'policies'
  params: {
    foundryHubPnaExemptionAssignmentId: foundryHubPnaExemptionAssignmentId
  }
}

// Entra ID app registrations cannot be created via Bicep.
// See ./modules/entra-app.bicep for manual / CLI instructions.
module entraApp './modules/entra-app.bicep' = {
  name: 'entraAppPlaceholder'
  params: {
    entraAppName: entraAppName
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

@description('Resource ID of the provisioned Fabric capacity.')
output fabricCapacityId string = fabricCapacity.outputs.capacityId

@description('URI of the provisioned Key Vault.')
output keyVaultUri string = keyVault.outputs.vaultUri

@description('Resource ID of the Storage account.')
output storageAccountId string = storage.outputs.storageAccountId

@description('Resource ID of the AI Foundry Hub.')
output foundryHubId string = aiFoundry.outputs.hubId

@description('Principal ID of the Foundry Hub system-assigned managed identity.')
output foundryHubPrincipalId string = aiFoundry.outputs.hubPrincipalId
