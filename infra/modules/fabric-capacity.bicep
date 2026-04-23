// ---------------------------------------------------------------------------
// fabric-capacity.bicep — Microsoft Fabric capacity
// ---------------------------------------------------------------------------

@description('Name of the Fabric capacity resource.')
param name string

@description('Azure region.')
param location string

@description('Fabric capacity SKU. F2 is the minimum tier that supports Data Agent.')
@allowed(['F2', 'F4', 'F8', 'F16', 'F32', 'F64', 'F128', 'F256', 'F512', 'F1024', 'F2048'])
param sku string = 'F2'

@description('UPN of the Fabric capacity administrator (e.g. admin@contoso.com).')
param adminMemberUpn string

@description('Resource tags.')
param tags object = {}

resource fabricCapacity 'Microsoft.Fabric/capacities@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    tier: 'Fabric'
  }
  properties: {
    administration: {
      members: empty(adminMemberUpn) ? [] : [adminMemberUpn]
    }
  }
}

@description('Resource ID of the Fabric capacity.')
output capacityId string = fabricCapacity.id
