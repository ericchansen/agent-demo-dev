#!/usr/bin/env bash
# Enable the Live Smoke workflow's GitHub OIDC -> Azure login in one command.
#
# Creates (or reuses) an Entra app registration + service principal, adds the
# GitHub Actions federated credential that lets the `Live Smoke` workflow call
# azure/login@v3 without a stored client secret, and pushes the resulting
# AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID values to the repo
# as GitHub Actions secrets.
#
# The script is idempotent: re-running it reuses the existing app, federated
# credential, role assignment, and secrets instead of creating duplicates.
#
# Use --dry-run to print every mutation without making changes.
#
# If Microsoft Graph mutations fail (interactive CAE challenge in a headless
# context, or insufficient Entra role), the script prints the exact
# federated-credential JSON and the `az ad app federated-credential create`
# command so a facilitator with the right permissions can finish by hand.
#
# Usage:
#   scripts/setup_oidc.sh [--dry-run] [--repo OWNER/REPO] [--branch main]
#       [--app-display-name NAME] [--app-id APPID]
#       [--subscription-id SUBID] [--resource-group RG] [--role Contributor]
set -euo pipefail

REPO="ericchansen/agent-demo-dev"
BRANCH="main"
APP_DISPLAY_NAME="agent-demo-dev-live-smoke"
APP_ID=""
SUBSCRIPTION_ID=""
RESOURCE_GROUP="rg-fabric-agent-dev"
ROLE="Contributor"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --app-display-name) APP_DISPLAY_NAME="$2"; shift 2 ;;
    --app-id) APP_ID="$2"; shift 2 ;;
    --subscription-id) SUBSCRIPTION_ID="$2"; shift 2 ;;
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

FED_CRED_NAME="github-actions-${BRANCH}"
SUBJECT="repo:${REPO}:ref:refs/heads/${BRANCH}"
ISSUER="https://token.actions.githubusercontent.com"
AUDIENCE="api://AzureADTokenExchange"

step()  { printf '\033[36m==> %s\033[0m\n' "$1"; }
skip()  { printf '\033[33m    (dry-run) %s\033[0m\n' "$1"; }
note()  { printf '    %s\n' "$1"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command '$1' is not on PATH." >&2; exit 1; }
}

fed_cred_json() {
  cat <<JSON
{
  "name": "${FED_CRED_NAME}",
  "issuer": "${ISSUER}",
  "subject": "${SUBJECT}",
  "description": "GitHub Actions OIDC for ${REPO} on ${BRANCH} (Live Smoke)",
  "audiences": ["${AUDIENCE}"]
}
JSON
}

manual_fallback() {
  local client_id="${1:-<APP_ID>}"
  echo ""
  echo "Could not complete the Microsoft Graph mutation automatically." >&2
  echo "A facilitator with Application Administrator (or app ownership) can run:" >&2
  echo ""
  echo "  # 1. Save this federated credential JSON to federated-credential.json :"
  fed_cred_json
  echo ""
  echo "  # 2. Create it:"
  echo "  az ad app federated-credential create --id ${client_id} --parameters federated-credential.json"
  echo ""
  echo "  # 3. Then set the GitHub secrets (AZURE_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID)."
}

require_cmd az
require_cmd gh

step "Verifying Azure CLI session"
if ! ACCOUNT_JSON="$(az account show 2>/dev/null)"; then
  echo "Not logged in to Azure CLI. Run 'az login' first." >&2
  exit 1
fi
[[ -z "$SUBSCRIPTION_ID" ]] && SUBSCRIPTION_ID="$(echo "$ACCOUNT_JSON" | az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
note "Subscription: ${SUBSCRIPTION_ID}"
note "Tenant:       ${TENANT_ID}"

step "Verifying GitHub CLI session"
gh auth status >/dev/null 2>&1 || { echo "Not logged in to GitHub CLI. Run 'gh auth login'." >&2; exit 1; }

CLIENT_ID="$APP_ID"
if [[ -z "$CLIENT_ID" ]]; then
  step "Resolving app registration '${APP_DISPLAY_NAME}'"
  EXISTING="$(az ad app list --display-name "$APP_DISPLAY_NAME" --query '[0].appId' -o tsv 2>/dev/null || true)"
  if [[ -n "$EXISTING" ]]; then
    CLIENT_ID="$EXISTING"
    note "Reusing existing app: ${CLIENT_ID}"
  elif [[ "$DRY_RUN" == "true" ]]; then
    skip "would create app registration '${APP_DISPLAY_NAME}'"
    CLIENT_ID="<new-app-id>"
  else
    step "Creating app registration '${APP_DISPLAY_NAME}'"
    if ! CLIENT_ID="$(az ad app create --display-name "$APP_DISPLAY_NAME" --query appId -o tsv)"; then
      manual_fallback ""
      exit 1
    fi
    note "Created app: ${CLIENT_ID}"
  fi
else
  note "Using provided app id: ${CLIENT_ID}"
fi

if [[ "$DRY_RUN" == "true" ]]; then
  skip "would ensure a service principal for app ${CLIENT_ID}"
elif [[ "$CLIENT_ID" != "<new-app-id>" ]]; then
  step "Ensuring service principal exists"
  if [[ -z "$(az ad sp show --id "$CLIENT_ID" --query id -o tsv 2>/dev/null || true)" ]]; then
    az ad sp create --id "$CLIENT_ID" >/dev/null 2>&1 || note "Could not create SP (may already exist or insufficient rights)."
  fi
fi

step "Configuring federated credential '${FED_CRED_NAME}'"
note "subject: ${SUBJECT}"
if [[ "$DRY_RUN" == "true" ]]; then
  skip "would create/verify federated credential:"
  fed_cred_json
else
  HAVE_CRED="$(az ad app federated-credential list --id "$CLIENT_ID" --query "[?subject=='${SUBJECT}'] | [0].name" -o tsv 2>/dev/null || true)"
  if [[ -n "$HAVE_CRED" ]]; then
    note "Federated credential already present (${HAVE_CRED}) — leaving as-is."
  else
    TMP="$(mktemp)"
    fed_cred_json > "$TMP"
    if ! az ad app federated-credential create --id "$CLIENT_ID" --parameters "$TMP" >/dev/null; then
      rm -f "$TMP"
      manual_fallback "$CLIENT_ID"
      exit 1
    fi
    rm -f "$TMP"
    note "Federated credential created."
  fi
fi

if [[ -n "$RESOURCE_GROUP" ]]; then
  step "Ensuring '${ROLE}' on resource group '${RESOURCE_GROUP}'"
  SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"
  if [[ "$DRY_RUN" == "true" ]]; then
    skip "would assign ${ROLE} to SP of ${CLIENT_ID} on ${SCOPE}"
  elif [[ "$CLIENT_ID" != "<new-app-id>" ]]; then
    az role assignment create --assignee "$CLIENT_ID" --role "$ROLE" --scope "$SCOPE" >/dev/null 2>&1 \
      && note "Role assignment ensured." \
      || note "Role assignment skipped (already present or insufficient rights)."
  fi
else
  note "Skipping role assignment (empty --resource-group)."
fi

step "Setting GitHub Actions secrets on ${REPO}"
set_secret() {
  local name="$1" value="$2"
  if [[ "$DRY_RUN" == "true" ]]; then
    skip "would set secret ${name}"
  else
    printf '%s' "$value" | gh secret set "$name" --repo "$REPO" --body -
    note "Set ${name}"
  fi
}
set_secret AZURE_CLIENT_ID "$CLIENT_ID"
set_secret AZURE_TENANT_ID "$TENANT_ID"
set_secret AZURE_SUBSCRIPTION_ID "$SUBSCRIPTION_ID"

echo ""
step "Done."
echo "Next:"
echo "  1. Set FOUNDRY_PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME for the Foundry check:"
echo "       gh secret set FOUNDRY_PROJECT_ENDPOINT --repo ${REPO}"
echo "       gh secret set MODEL_DEPLOYMENT_NAME --repo ${REPO}"
echo "  2. Trigger required-mode smoke for only the platform you teach, e.g.:"
echo "       gh workflow run 'Live Smoke' --repo ${REPO} -f require_foundry=true"
echo "  3. Watch it:  gh run watch --repo ${REPO}"
