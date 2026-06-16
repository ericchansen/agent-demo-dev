// ---------------------------------------------------------------------------
// app-insights.bicep — Application Insights for Foundry agent tracing
//
// Creates a workspace-based Application Insights resource and a Log Analytics
// workspace to back it. Connect this to the Foundry project (via the portal or
// SDK) to enable agent traces, conversations, and response monitoring.
// ---------------------------------------------------------------------------

@description('Name of the Application Insights resource.')
param name string

@description('Azure region.')
param location string

@description('Name of the Log Analytics workspace backing Application Insights.')
param logAnalyticsWorkspaceName string = '${name}-law'

@description('Public network access for ingestion and query endpoints.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Resource tags.')
param tags object = {}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: publicNetworkAccess
    publicNetworkAccessForQuery: publicNetworkAccess
  }
}

@description('Resource ID of the Application Insights resource.')
output appInsightsId string = appInsights.id

@description('Connection string for Application Insights (used by Foundry tracing).')
output connectionString string = appInsights.properties.ConnectionString

@description('Instrumentation key (legacy, some SDKs still reference it).')
output instrumentationKey string = appInsights.properties.InstrumentationKey
