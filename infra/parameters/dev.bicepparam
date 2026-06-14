using '../main.bicep'

param fabricCapacityName = 'fabricagentdemodev'
param keyVaultName = 'fsa-agent-kv-dev-2026'
param entraAppName = 'FSA-WorkIQ-Agent-Dev'
param fabricCapacitySku = 'F2'
param fabricAdminUpn = 'admin@MngEnvMCAP529863.onmicrosoft.com'
param storageAccountName = 'fsaagentstorage2026d'
param cogServicesName = 'fabricagentaidev2026'
param foundryHubCogServicesName = 'fsa-hub-dev-2026'
param foundryHubName = 'fabric-agent-hub-dev'
param publicNetworkAccess = 'Enabled'
param foundryHubStorageRoleAssignmentName = 'c52d7250-ea78-4536-b15a-d45b2bad6c97'

// Exempt the dev hub from the management-group "modify" policy that otherwise
// forces publicNetworkAccess=Disabled and blocks the ai.azure.com portal.
param foundryHubPnaExemptionAssignmentId = '/providers/Microsoft.Management/managementGroups/9c74def4-ef0a-418a-8dc7-1e7a1e85ce10/providers/Microsoft.Authorization/policyAssignments/mcapsgovdeploypolicies'
