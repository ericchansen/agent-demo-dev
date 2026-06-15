<#
.SYNOPSIS
    Enable the Live Smoke workflow's GitHub OIDC -> Azure login in one command.

.DESCRIPTION
    Creates (or reuses) an Entra app registration + service principal, adds the
    GitHub Actions federated credential that lets the `Live Smoke` workflow call
    `azure/login@v3` without a stored client secret, and pushes the resulting
    AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID values to the repo
    as GitHub Actions secrets.

    The script is idempotent: re-running it reuses the existing app, federated
    credential, role assignment, and secrets instead of creating duplicates.

    Run with -DryRun to print every mutation without making changes.

    If Microsoft Graph mutations fail (for example an interactive Conditional
    Access / CAE challenge in a headless context, or insufficient Entra role),
    the script prints the exact federated-credential JSON and the
    `az ad app federated-credential create` command so a facilitator with the
    right permissions can finish the step by hand.

.PARAMETER Repo
    GitHub repository in OWNER/REPO form. Default: ericchansen/agent-demo-dev.

.PARAMETER Branch
    Branch the workflow runs on (the OIDC subject pins to it). Default: main.

.PARAMETER EnvironmentName
    Optional GitHub Actions environment name. When set, also creates a
    federated credential for workflows whose jobs run in that environment.

.PARAMETER AppDisplayName
    Entra app display name to create/reuse. Default: agent-demo-dev-live-smoke.

.PARAMETER AppId
    Use an existing app (client) id instead of creating/looking up by name.

.PARAMETER SubscriptionId
    Azure subscription id. Defaults to the current `az account` subscription.

.PARAMETER ResourceGroup
    Resource group to grant the service principal Contributor on. Default:
    rg-fabric-agent-dev. Pass an empty string to skip role assignment.

.PARAMETER Role
    Azure RBAC role for the service principal. Default: Contributor.

.PARAMETER DryRun
    Print actions without changing anything.

.EXAMPLE
    ./scripts/setup_oidc.ps1 -DryRun

.EXAMPLE
    ./scripts/setup_oidc.ps1 -SubscriptionId 9450bd3b-96c5-48b2-bfdf-3374304efbd7
#>
[CmdletBinding()]
param(
    [string]$Repo = "ericchansen/agent-demo-dev",
    [string]$Branch = "main",
    [string]$EnvironmentName = "dev",
    [string]$AppDisplayName = "agent-demo-dev-live-smoke",
    [string]$AppId = "",
    [string]$SubscriptionId = "",
    [string]$ResourceGroup = "rg-fabric-agent-dev",
    [string]$Role = "Contributor",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Issuer = "https://token.actions.githubusercontent.com"
$Audience = "api://AzureADTokenExchange"

function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Skip { param([string]$Message) Write-Host "    (dry-run) $Message" -ForegroundColor Yellow }

function Test-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not on PATH. Install it and retry."
    }
}

function Get-FederatedCredentialJson {
    param(
        [string]$Name,
        [string]$Subject,
        [string]$Description
    )
    @{
        name        = $Name
        issuer      = $Issuer
        subject     = $Subject
        description = $Description
        audiences   = @($Audience)
    } | ConvertTo-Json -Depth 4
}

function Show-ManualFallback {
    param([string]$ClientId)
    Write-Host ""
    Write-Host "Could not complete the Microsoft Graph mutation automatically." -ForegroundColor Red
    Write-Host "A facilitator with Application Administrator (or app ownership) can run:" -ForegroundColor Red
    Write-Host ""
    $json = Get-FederatedCredentialJson -Name "github-actions-$Branch" -Subject "repo:${Repo}:ref:refs/heads/$Branch" -Description "GitHub Actions OIDC for $Repo on $Branch"
    $tmp = "federated-credential.json"
    Write-Host "  # 1. Save this federated credential JSON to $tmp :"
    Write-Host $json
    Write-Host ""
    Write-Host "  # 2. Create it (replace <APP_ID> if blank below):"
    $idForCmd = if ($ClientId) { $ClientId } else { "<APP_ID>" }
    Write-Host "  az ad app federated-credential create --id $idForCmd --parameters $tmp"
    Write-Host ""
    Write-Host "  # 3. Then set the GitHub secrets (see the printed values above)."
}

Test-Command az
Test-Command gh

Write-Step "Verifying Azure CLI session"
try { $account = az account show 2>$null | ConvertFrom-Json } catch { $account = $null }
if (-not $account) { throw "Not logged in to Azure CLI. Run 'az login' first." }
if (-not $SubscriptionId) { $SubscriptionId = $account.id }
$TenantId = $account.tenantId
Write-Host "    Subscription: $SubscriptionId"
Write-Host "    Tenant:       $TenantId"

Write-Step "Verifying GitHub CLI session"
gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Not logged in to GitHub CLI. Run 'gh auth login' first." }

# --- Resolve or create the app registration -------------------------------
$ClientId = $AppId
if (-not $ClientId) {
    Write-Step "Resolving app registration '$AppDisplayName'"
    $existing = az ad app list --display-name $AppDisplayName --query "[0].appId" -o tsv 2>$null
    if ($existing) {
        $ClientId = $existing
        Write-Host "    Reusing existing app: $ClientId"
    }
    elseif ($DryRun) {
        Write-Skip "would create app registration '$AppDisplayName'"
        $ClientId = "<new-app-id>"
    }
    else {
        Write-Step "Creating app registration '$AppDisplayName'"
        try {
            $ClientId = az ad app create --display-name $AppDisplayName --query appId -o tsv
        }
        catch {
            Show-ManualFallback -ClientId ""
            throw
        }
        if (-not $ClientId) { Show-ManualFallback -ClientId ""; throw "App creation returned no appId." }
        Write-Host "    Created app: $ClientId"
    }
}
else {
    Write-Host "    Using provided app id: $ClientId"
}

# --- Ensure a service principal exists -------------------------------------
if ($DryRun) {
    Write-Skip "would ensure a service principal for app $ClientId"
}
elseif ($ClientId -ne "<new-app-id>") {
    Write-Step "Ensuring service principal exists"
    $sp = az ad sp show --id $ClientId --query id -o tsv 2>$null
    if (-not $sp) {
        try { az ad sp create --id $ClientId | Out-Null }
        catch { Write-Host "    Could not create service principal (may already exist or insufficient rights)." -ForegroundColor Yellow }
    }
}

function Set-FederatedCredential {
    param(
        [string]$Name,
        [string]$Subject,
        [string]$Description
    )

    Write-Step "Configuring federated credential '$Name'"
    Write-Host "    subject: $Subject"
    if ($DryRun) {
        Write-Skip "would create/verify federated credential:"
        Write-Host (Get-FederatedCredentialJson -Name $Name -Subject $Subject -Description $Description)
        return
    }

    $haveCred = az ad app federated-credential list --id $ClientId --query "[?subject=='$Subject'] | [0].name" -o tsv 2>$null
    if ($haveCred) {
        Write-Host "    Federated credential already present ($haveCred) — leaving as-is."
        return
    }

    $tmp = New-TemporaryFile
    Get-FederatedCredentialJson -Name $Name -Subject $Subject -Description $Description | Set-Content -Path $tmp -Encoding utf8
    try {
        az ad app federated-credential create --id $ClientId --parameters $tmp | Out-Null
        Write-Host "    Federated credential created."
    }
    catch {
        Remove-Item $tmp -ErrorAction SilentlyContinue
        Show-ManualFallback -ClientId $ClientId
        throw
    }
    Remove-Item $tmp -ErrorAction SilentlyContinue
}

Set-FederatedCredential `
    -Name "github-actions-$Branch" `
    -Subject "repo:${Repo}:ref:refs/heads/$Branch" `
    -Description "GitHub Actions OIDC for $Repo on $Branch"

if ($EnvironmentName) {
    Set-FederatedCredential `
        -Name "github-actions-env-$EnvironmentName" `
        -Subject "repo:${Repo}:environment:$EnvironmentName" `
        -Description "GitHub Actions OIDC for $Repo environment $EnvironmentName"
}

# --- Role assignment so azure/login can act --------------------------------
if ($ResourceGroup) {
    Write-Step "Ensuring '$Role' on resource group '$ResourceGroup'"
    if ($DryRun) {
        Write-Skip "would assign $Role to SP of $ClientId on /subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
    }
    elseif ($ClientId -ne "<new-app-id>") {
        $scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
        try {
            az role assignment create --assignee $ClientId --role $Role --scope $scope 2>$null | Out-Null
            Write-Host "    Role assignment ensured."
        }
        catch {
            Write-Host "    Role assignment skipped (already present or insufficient rights)." -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "    Skipping role assignment (empty -ResourceGroup)."
}

# --- GitHub secrets ---------------------------------------------------------
Write-Step "Setting GitHub Actions secrets on $Repo"
$secrets = [ordered]@{
    AZURE_CLIENT_ID       = $ClientId
    AZURE_TENANT_ID       = $TenantId
    AZURE_SUBSCRIPTION_ID = $SubscriptionId
}
foreach ($name in $secrets.Keys) {
    $value = $secrets[$name]
    if ($DryRun) {
        Write-Skip "would set secret $name"
    }
    else {
        gh secret set $name --repo $Repo --body $value
        Write-Host "    Set $name"
    }
}

Write-Host ""
Write-Step "Done."
Write-Host "Next:"
Write-Host "  1. Set FOUNDRY_PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME for the Foundry check:"
Write-Host "       gh secret set FOUNDRY_PROJECT_ENDPOINT --repo $Repo"
Write-Host "       gh secret set MODEL_DEPLOYMENT_NAME --repo $Repo"
Write-Host "  2. Trigger required-mode smoke for only the platform you teach, e.g.:"
Write-Host "       gh workflow run 'Live Smoke' --repo $Repo -f require_foundry=true"
Write-Host "  3. Watch it:  gh run watch --repo $Repo"
