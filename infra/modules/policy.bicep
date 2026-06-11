// ---------------------------------------------------------------------------
// policy.bicep — Azure Policy assignments at Resource Group scope
//
// Assigns three built-in policies in Audit mode to detect and surface
// configuration drift without blocking existing workloads.
//
// Escalation path:
//   Change effect from 'Audit' to 'Deny' in each assignment once all
//   resources in the RG are compliant. Requires Owner role on the RG.
//
// Assignments:
//   1. Storage — disable shared key access (built-in: b2982f36)
//   2. Cognitive Services — disable local authentication (built-in: 71ef260a)
//   3. AI Machine Learning — disable public network access (built-in: a6fb4358)
// ---------------------------------------------------------------------------

// No parameters required — assignments are RG-scoped by targetScope on main.bicep.

// ── 1. Storage accounts should disable shared-key access ────────────────────
resource policyStorageNoSharedKey 'Microsoft.Authorization/policyAssignments@2023-04-01' = {
  name: 'fsa-storage-no-sharedkey'
  properties: {
    displayName: '[FSA] Storage — disable shared-key access'
    description: 'Audit storage accounts that still allow shared-key (access-key) authentication. Entra identity-based auth should be used exclusively.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/b2982f36-99f2-4db5-8eff-283140c09693'
    // Override built-in effect to Audit so existing non-compliant resources are surfaced, not blocked.
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}

// ── 2. Cognitive Services accounts should disable local authentication ───────
resource policyCogsvcNoLocalAuth 'Microsoft.Authorization/policyAssignments@2023-04-01' = {
  name: 'fsa-cogsvc-no-localauth'
  properties: {
    displayName: '[FSA] Cognitive Services — disable local auth'
    description: 'Audit Cognitive Services accounts that allow API-key (local) authentication. Entra token-based auth should be used exclusively.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/71ef260a-8f18-47b7-abcae-2e13a3a99b5f'
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}

// ── 3. Azure Machine Learning workspaces should disable public network access ─
resource policyFoundryNoPubNet 'Microsoft.Authorization/policyAssignments@2023-04-01' = {
  name: 'fsa-foundry-no-pubnet'
  properties: {
    displayName: '[FSA] AI Foundry Hub — disable public network access'
    description: 'Audit Azure Machine Learning workspaces (Foundry hubs/projects) that allow public network access.'
    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/a6fb4358-5bf4-4ad7-ba82-2cd2f41ce5e8'
    parameters: {
      effect: {
        value: 'Audit'
      }
    }
    enforcementMode: 'Default'
  }
}
