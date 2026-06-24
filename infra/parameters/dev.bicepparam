using '../main.bicep'

param fabricCapacityName = 'salesagent'
param keyVaultName = 'kv-sales-agent'
param entraAppName = 'sales-agent-app'
param fabricCapacitySku = 'F2'
param fabricAdminUpn = 'admin@MngEnvMCAP529863.onmicrosoft.com'
param storageAccountName = 'salesagentstg'
param cogServicesName = 'salesagentais'
param appInsightsName = 'sales-agent-insights'
param publicNetworkAccess = 'Enabled'
param enableRoleAssignments = false
param enablePolicyAssignments = false
param budgetName = 'sales-agent-budget'
param budgetAmount = 350
// Set at deploy time to activate budget alerts without storing recipient
// addresses in source, for example:
//   --parameters budgetAlertEmails='["facilitator@example.com"]'
param budgetAlertEmails = []
