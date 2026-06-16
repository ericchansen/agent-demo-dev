using '../main.bicep'

param fabricCapacityName = 'fabricagentdemodev'
param keyVaultName = 'fsa-agent-kv-dev-2026'
param entraAppName = 'FSA-WorkIQ-Agent-Dev'
param fabricCapacitySku = 'F2'
param fabricAdminUpn = 'admin@MngEnvMCAP529863.onmicrosoft.com'
param storageAccountName = 'fsaagentstorage2026d'
param containerRegistryName = 'fsaagentacr2026d'
param cogServicesName = 'fabricagentaidev2026'
param appInsightsName = 'fsa-agent-insights-dev'
param publicNetworkAccess = 'Enabled'
param enableRoleAssignments = false
param enablePolicyAssignments = false
param budgetName = 'fsa-dev-monthly-budget'
param budgetAmount = 350
// Set at deploy time to activate budget alerts without storing recipient
// addresses in source, for example:
//   --parameters budgetAlertEmails='["facilitator@example.com"]'
param budgetAlertEmails = []
