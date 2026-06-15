// ---------------------------------------------------------------------------
// container-registry.bicep — ACR for Foundry Hosted Agent images
// ---------------------------------------------------------------------------

@description('Name of the Azure Container Registry.')
param name string

@description('Azure region.')
param location string

@description('Container Registry SKU.')
@allowed(['Basic', 'Standard', 'Premium'])
param skuName string = 'Premium'

@description('Public network access for the registry. Hosted Agents require public ACR pull access during preview.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Disabled'

@description('Resource tags.')
param tags object = {}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: publicNetworkAccess
    networkRuleBypassOptions: 'AzureServices'
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'disabled'
      }
      retentionPolicy: {
        days: 7
        status: 'enabled'
      }
    }
  }
}

@description('Resource ID of the Container Registry.')
output registryId string = registry.id

@description('Login server for docker push/pull.')
output loginServer string = registry.properties.loginServer
