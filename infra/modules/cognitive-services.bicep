// ---------------------------------------------------------------------------
// cognitive-services.bicep — Azure AI / Cognitive Services accounts
//
// Deploys one Cognitive Services account. Call this module once per account.
//
// Security posture enforced:
//   • disableLocalAuth = true          → API-key auth blocked; Entra tokens only
//   • publicNetworkAccess = Disabled   → no direct internet exposure
//
// ⚠️  MANUAL STEP BEFORE DISABLING PUBLIC ACCESS:
//   Confirm all consumers (Foundry hub, orchestrator containers) reach this
//   account via private endpoint or a VNet-integrated runtime. Setting
//   publicNetworkAccess=Disabled without an endpoint will make the account
//   unreachable from outside Azure virtual networks.
// ---------------------------------------------------------------------------

@description('Name of the Cognitive Services account.')
param name string

@description('Azure region.')
param location string

@description('Cognitive Services kind (e.g. AIServices, OpenAI, CognitiveServices).')
param kind string = 'AIServices'

@description('SKU name.')
@allowed(['S0', 'S1', 'S2', 'S3', 'F0'])
param skuName string = 'S0'

@description('Custom subdomain name (required when updating existing accounts that already have one).')
param customSubDomainName string = ''

@description('Resource tags.')
param tags object = {}

resource cogAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // Block API-key (local) auth; callers must present an Entra token.
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    customSubDomainName: empty(customSubDomainName) ? null : customSubDomainName
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

@description('Resource ID of the Cognitive Services account.')
output accountId string = cogAccount.id

@description('Principal ID of the system-assigned managed identity.')
output principalId string = cogAccount.identity.principalId
