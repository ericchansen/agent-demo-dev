// ---------------------------------------------------------------------------
// foundry-project.bicep — Azure AI Foundry Project (MachineLearningServices)
//
// Declares the workshop project (`fsa-project-dev`) as a child of the Foundry
// hub so that redeploying infra reproduces the FULL workshop environment, not
// just the hub. Previously the project was bootstrapped out-of-band via
// `az ml workspace create --kind Project`, which created drift risk: an
// `az deployment group create` did not guarantee the project existed.
//
// The project inherits networking, storage, and key vault from its parent hub.
// ---------------------------------------------------------------------------

@description('Name of the AI Foundry Project (MachineLearningServices workspace, kind Project).')
param projectName string

@description('Azure region. Should match the parent hub region.')
param location string

@description('Resource ID of the parent AI Foundry Hub workspace.')
param hubResourceId string

@description('Resource tags.')
param tags object = {}

// ── AI Foundry Project ──────────────────────────────────────────────────────
resource project 'Microsoft.MachineLearningServices/workspaces@2025-06-01' = {
  name: projectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // A project derives its data plane (storage, key vault, networking) from
    // the hub it is parented to. Only the hub link is required here.
    hubResourceId: hubResourceId
  }
}

@description('Resource ID of the Foundry Project.')
output projectId string = project.id

@description('Principal ID of the project system-assigned managed identity.')
output projectPrincipalId string = project.identity.principalId

@description('Discovery URL used by the azure-ai-projects SDK and the Foundry portal.')
output projectName string = project.name
