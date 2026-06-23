// ---------------------------------------------------------------------------
// main.bicep — Top-level orchestration for Sales Agent Demo
//
// Uses the MODERN Foundry architecture (CognitiveServices/accounts + project)
// exclusively. No legacy hub-based (MachineLearningServices) resources.
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

@description('Name of the Azure Storage account for agent artifacts and reports.')
param storageAccountName string

@description('Name of the Azure Container Registry used for Foundry Hosted Agent images.')
param containerRegistryName string

@description('Name of the AI Services account (Microsoft.CognitiveServices/accounts, kind=AIServices). This is the modern Foundry resource that hosts the agent SDK endpoint.')
param cogServicesName string

@description('Name of the Application Insights resource for Foundry agent tracing.')
param appInsightsName string = ''

@description('Public network access for resources. Enabled by default for demo accessibility.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Whether to create RBAC role assignments. Disabled by default for demo simplicity (avoids needing Owner role).')
param enableRoleAssignments bool = false

@description('Whether to create Azure Policy assignments. Disabled by default for demo simplicity.')
param enablePolicyAssignments bool = false

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

module appInsights './modules/app-insights.bicep' = if (!empty(appInsightsName)) {
  name: 'appInsights'
  params: {
    name: appInsightsName
    location: location
    publicNetworkAccess: publicNetworkAccess
    tags: tags
  }
}

module policies './modules/policy.bicep' = {
  name: 'policies'
  params: {
    enablePolicyAssignments: enablePolicyAssignments
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

@description('Resource ID of the AI Services account (modern Foundry). The Foundry project is a child resource created via SDK or Azure portal.')
output cogServicesId string = cogServices.outputs.accountId

@description('Application Insights connection string for Foundry agent tracing. Connect this in the Foundry portal under Traces > Connect.')
output appInsightsConnectionString string = !empty(appInsightsName) ? appInsights!.outputs.connectionString : ''
