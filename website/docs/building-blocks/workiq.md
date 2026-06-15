---
sidebar_position: 2
title: WorkIQ
---

# WorkIQ & M365 Activity Signals

WorkIQ provides structured access to a user's Microsoft 365 activity — emails, meetings, file interactions, and engagement patterns. When connected to your agent, it transforms generic data lookups into personalized, context-aware responses.

## What WorkIQ provides

| Signal | Description | Example |
|---|---|---|
| **Email activity** | Messages sent/received with contacts | "You sent 12 emails to Tailspin Toys this month" |
| **Meeting activity** | Calendar events with attendees | "You had 4 meetings with their procurement team" |
| **File sharing** | Documents shared with contacts | "They opened the pricing proposal on June 2" |
| **Engagement trends** | Activity patterns over time | "Engagement with this account is increasing" |

These signals are scoped to the authenticated user — the agent can only see *your* activity, enforced by Microsoft Graph's permission model.

## How it connects

### CLI surface (MCP server)

```json
{
  "mcpServers": {
    "workiq": {
      "type": "npm",
      "package": "@anthropic-ai/workiq",
      "args": []
    }
  }
}
```

### Foundry surface (platform tool)

In Azure AI Foundry, WorkIQ is registered as `WorkIQPreviewTool` — a platform tool that uses OBO (on-behalf-of) authentication to access the user's M365 data.

## Authentication

WorkIQ uses the [on-behalf-of (OBO) flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow). The agent acts *as* the signed-in user, not with its own identity. This means:

- The agent sees only what *you* can see
- Different users get different results
- No admin consent needed for basic activity signals
- Compliant with M365 data residency and privacy policies

> ⚠️ **Demo tenant note:** The current demo environment uses mock M365 activity data. Production deployments use real OBO authentication against Microsoft Graph.

## Demo-safe fallback

The quota pipeline accepts synthetic WorkIQ-shaped activity when a tenant does not have WorkIQ provisioned. The
fallback is clearly cited as synthetic in generated reports, but it still exercises the same engagement adjustment
logic so Day 1 and CI can run without tenant-specific credentials.

## Privacy and security

WorkIQ respects Microsoft Graph's permission model:

- **User-scoped** — the agent cannot access other users' data
- **Consent-based** — the user (or admin) must grant access
- **Auditable** — all access is logged in the Microsoft 365 audit log
- **Revocable** — permissions can be withdrawn at any time

> 📖 [Microsoft Graph permissions](https://learn.microsoft.com/graph/permissions-overview) · [M365 compliance](https://learn.microsoft.com/microsoft-365/compliance/)

## Further reading

- [On-behalf-of auth flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Microsoft Graph API reference](https://learn.microsoft.com/graph/api/overview)
- [M365 Copilot extensibility](https://learn.microsoft.com/microsoft-365-copilot/extensibility/)
