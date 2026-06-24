using '../main.bicep'

param fabricCapacityName = 'salesagentdemo'
param keyVaultName = 'kv-sales-agent-demo'
param entraAppName = 'sales-agent-demo-app'
param fabricCapacitySku = 'F2'
param fabricAdminUpn = 'admin@MngEnvMCAP529863.onmicrosoft.com'
param storageAccountName = 'salesagentdemostg'
param containerRegistryName = 'salesagentdemoacr'
param cogServicesName = 'salesagentdemoais'
param appInsightsName = 'sales-agent-demo-insights'
param publicNetworkAccess = 'Enabled'
param enableRoleAssignments = false
param enablePolicyAssignments = false
param budgetName = 'sales-agent-demo-budget'
param budgetAmount = 350
// Set at deploy time to activate budget alerts without storing recipient
// addresses in source, for example:
//   --parameters budgetAlertEmails='["facilitator@example.com"]'
param budgetAlertEmails = []
