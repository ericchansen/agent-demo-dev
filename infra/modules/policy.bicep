// ---------------------------------------------------------------------------
// policy.bicep — Azure Policy assignments at Resource Group scope
//
// Assigns built-in policies in Audit mode to detect and surface
// configuration drift without blocking existing workloads.
//
// Escalation path:
//   Change effect from 'Audit' to 'Deny' in each assignment once all
//   resources in the RG are compliant. Requires Owner role on the RG.
//
// Assignments (all verified via `az policy definition show`):
//   1. Storage — prevent shared key access       (8c6a50c6)
//   2. AI Services — disable local key access     (71ef260a-...-abcb-62d0673d94dc)
//   3. AI Services — restrict network access      (037eea7a)
// ---------------------------------------------------------------------------

@description('Whether to create resource-group policy assignments. Requires Owner or Resource Policy Contributor; set false for Contributor-only CI deploys.')
param enablePolicyAssignments bool = true

// ── 1. Storage accounts should prevent shared-key access ────────────────────
resource policyStorageNoSharedKey 'Microsoft.Authorization/policyAssignments@2023-04-01' = if (enablePolicyAssignments) {
  name: 'fsa-storage-no-sharedkey'
  properties: {
    displayName: '[FSA] Storage — prevent shared-key access'
    description: 'Audit storage accounts that still allow shared-key (access-key) authentication. Entra identity-based auth should be used exclusively.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/8c6a50c6-9ffd-4ae7-986f-5fa6111f9a54'
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}

// ── 2. AI Services resources should have key access disabled ─────────────────
resource policyAiSvcNoLocalAuth 'Microsoft.Authorization/policyAssignments@2023-04-01' = if (enablePolicyAssignments) {
  name: 'fsa-aisvc-no-localauth'
  properties: {
    displayName: '[FSA] AI Services — disable local key access'
    description: 'Audit Azure AI Services / Cognitive Services accounts that allow API-key (local) authentication. Entra token-based auth should be used exclusively.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/71ef260a-8f18-47b7-abcb-62d0673d94dc'
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}

// ── 3. AI Services resources should restrict network access ─────────────────
resource policyAiSvcRestrictNetwork 'Microsoft.Authorization/policyAssignments@2023-04-01' = if (enablePolicyAssignments) {
  name: 'fsa-aisvc-restrict-net'
  properties: {
    displayName: '[FSA] AI Services — restrict network access'
    description: 'Audit Azure AI Services / Cognitive Services accounts that do not restrict public network access.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/037eea7a-bd0a-46c5-9a66-03aea78705d3'
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}
