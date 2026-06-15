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
param foundryProjectName = 'fsa-project-dev'
param publicNetworkAccess = 'Enabled'
param foundryHubStorageRoleAssignmentName = 'c52d7250-ea78-4536-b15a-d45b2bad6c97'
param budgetName = 'fsa-dev-monthly-budget'
param budgetAmount = 350
// Set at deploy time to activate budget alerts without storing recipient
// addresses in source, for example:
//   --parameters budgetAlertEmails='["facilitator@example.com"]'
param budgetAlertEmails = []

// The dev hub is exempted from the management-group "modify" policy that
// otherwise forces publicNetworkAccess=Disabled and blocks the ai.azure.com
// portal. Creating the exemption requires the MG-level
// 'Microsoft.Authorization/policyAssignments/exempt/action' permission, which
// the CI OIDC principal does NOT have — so this is left empty here to keep the
// recurring CI deploy green. The exemption is applied ONCE by a privileged
// admin (it persists independently and keeps the hub reachable across
// redeploys). To (re)create it, run as an admin:
//
//   az policy exemption create --name exempt-hub-pna-dev \
//     --resource-group rg-fabric-agent-dev --exemption-category Waiver \
//     --policy-assignment /providers/Microsoft.Management/managementGroups/<your-management-group-id>/providers/Microsoft.Authorization/policyAssignments/mcapsgovdeploypolicies
//
// Or deploy infra/main.bicep with this param set, using credentials that hold
// the MG-level exempt/action permission (e.g. manual workflow_dispatch).
param foundryHubPnaExemptionAssignmentId = ''
