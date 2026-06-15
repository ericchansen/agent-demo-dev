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

@description('Name of the Azure Container Registry used for Foundry Hosted Agent images.')
param containerRegistryName string

@description('Name of the primary Cognitive Services / AI Services account (fabricagentai2026).')
param cogServicesName string

@description('Name of the AI Foundry Hub Cognitive Services account (fsa-hub-2026).')
param foundryHubCogServicesName string

@description('Name of the AI Foundry Hub workspace (fabric-agent-hub).')
param foundryHubName string

@description('Name of the AI Foundry Project workspace (kind Project) parented to the hub. The workshop registers agents against this project.')
param foundryProjectName string

@description('Public network access for demo-facing resources. Keep Disabled for production; dev can override to Enabled for portal access.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Disabled'

@description('Optional existing role assignment name for the Foundry hub managed identity on storage. Use only to make redeploys idempotent when the assignment already exists with a non-default name.')
param foundryHubStorageRoleAssignmentName string = ''

@description('Whether to create RBAC role assignments. Requires Owner or User Access Administrator; dev CI uses false because the OIDC principal is Contributor-scoped.')
param enableRoleAssignments bool = true

@description('Optional resource ID of an external (management-group) policy assignment whose "modify" effect forces Foundry hubs to publicNetworkAccess=Disabled. When set, a Waiver exemption is created so the dev hub stays reachable. Leave empty in production.')
param foundryHubPnaExemptionAssignmentId string = ''

@description('Whether to create resource-group Azure Policy assignments. Requires Owner or Resource Policy Contributor; dev CI uses false because the OIDC principal is Contributor-scoped.')
param enablePolicyAssignments bool = true

@description('Resource tags applied to every resource.')
param tags object = {}

@description('Optional budget name. The budget is deployed only when budgetAlertEmails has at least one address.')
param budgetName string = 'fsa-demo-monthly-budget'

@description('Monthly budget amount in USD for the workshop resource group.')
@minValue(1)
param budgetAmount int = 350

@description('Budget alert start date. Azure requires the first day of a month in ISO 8601 format.')
param budgetStartDate string = utcNow('yyyy-MM-01T00:00:00Z')

@description('Email addresses for budget alerts. Leave empty to skip budget creation in shared/dev automation.')
param budgetAlertEmails array = []

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

module containerRegistry './modules/container-registry.bicep' = {
  name: 'containerRegistry'
  params: {
    name: containerRegistryName
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
    enableRoleAssignments: enableRoleAssignments
    tags: tags
  }
}

module foundryProject './modules/foundry-project.bicep' = {
  name: 'foundryProject'
  params: {
    projectName: foundryProjectName
    location: location
    hubResourceId: aiFoundry.outputs.hubId
    tags: tags
  }
}

module policies './modules/policy.bicep' = {
  name: 'policies'
  params: {
    enablePolicyAssignments: enablePolicyAssignments
    foundryHubPnaExemptionAssignmentId: foundryHubPnaExemptionAssignmentId
  }
}

module monthlyBudget './modules/budget.bicep' = if (length(budgetAlertEmails) > 0) {
  name: 'monthlyBudget'
  params: {
    name: budgetName
    amount: budgetAmount
    startDate: budgetStartDate
    contactEmails: budgetAlertEmails
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

@description('Login server for the Container Registry used by hosted-agent deployments.')
output containerRegistryEndpoint string = containerRegistry.outputs.loginServer

@description('Resource ID of the AI Foundry Hub.')
output foundryHubId string = aiFoundry.outputs.hubId

@description('Principal ID of the Foundry Hub system-assigned managed identity.')
output foundryHubPrincipalId string = aiFoundry.outputs.hubPrincipalId

@description('Resource ID of the Foundry Project where workshop agents are registered.')
output foundryProjectId string = foundryProject.outputs.projectId
