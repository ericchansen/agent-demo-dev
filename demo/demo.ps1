<#
.SYNOPSIS
    Launch the Fabric Sales Agent demo in an isolated Copilot CLI environment.

.DESCRIPTION
    Uses COPILOT_HOME to isolate from personal MCP servers, skills, and plugins.
    Workspace MCP configs (.github/mcp.json) still load — that's the demo content.

.PARAMETER Setup
    Run first-time setup: create isolated home dir and authenticate.

.EXAMPLE
    # First time — authenticate once
    .\demo\demo.ps1 -Setup

    # Every time after — just launch
    .\demo\demo.ps1
#>
[CmdletBinding()]
param(
    [switch]$Setup
)

$ErrorActionPreference = 'Stop'
$DemoHome = Join-Path $env:USERPROFILE '.copilot-demo'

if ($Setup) {
    Write-Host "`n=== Fabric Sales Agent — Demo Setup ===" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $DemoHome -Force | Out-Null
    Write-Host "Created isolated COPILOT_HOME: $DemoHome"
    Write-Host "Authenticating (one-time)...`n" -ForegroundColor Yellow

    $env:COPILOT_HOME = $DemoHome
    copilot auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Authentication failed. Re-run: .\demo\demo.ps1 -Setup"
        return
    }
    Write-Host "`n✅ Setup complete. Launch the demo with: .\demo\demo.ps1" -ForegroundColor Green
    return
}

# Verify setup
if (-not (Test-Path $DemoHome)) {
    Write-Error "Demo not set up yet. Run: .\demo\demo.ps1 -Setup"
    return
}

Write-Host "=== Fabric Sales Agent Demo ===" -ForegroundColor Cyan
Write-Host "COPILOT_HOME: $DemoHome (isolated from personal config)" -ForegroundColor DarkGray

# Ensure Fabric capacity is running
$CapacityId = '/subscriptions/9450bd3b-96c5-48b2-bfdf-3374304efbd7/resourceGroups/rg-fabric-agent/providers/Microsoft.Fabric/capacities/fabricagentdemo'
$state = az rest --method GET --url "https://management.azure.com${CapacityId}?api-version=2023-11-01" --query "properties.state" -o tsv 2>$null
if ($state -eq 'Paused') {
    Write-Host "Resuming Fabric capacity..." -ForegroundColor Yellow
    az rest --method POST --url "https://management.azure.com${CapacityId}/resume?api-version=2023-11-01" 2>$null | Out-Null
    Start-Sleep -Seconds 5
    Write-Host "✅ Capacity resumed" -ForegroundColor Green
} elseif ($state -eq 'Active') {
    Write-Host "✅ Fabric capacity is active" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not check Fabric capacity (state: $state)" -ForegroundColor Yellow
}

Write-Host ""
$env:COPILOT_HOME = $DemoHome
copilot --no-custom-instructions
