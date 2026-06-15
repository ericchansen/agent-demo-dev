param(
    [ValidateSet("fabric", "databricks")]
    [string]$DataSource = "fabric",

    [string]$CustomerName = "Tailspin Toys",

    [string]$OutputDir = "output\foundry-local-devui"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Checking Foundry Local CLI (optional)..."
$foundryCommand = Get-Command foundry -ErrorAction SilentlyContinue
if ($foundryCommand) {
    foundry --version
    foundry service status
}
else {
    Write-Host "Foundry Local CLI is not installed. Deterministic multi-agent checks can still run."
    Write-Host "Install later with: winget install Microsoft.FoundryLocal"
}

$resolvedOutput = Join-Path $OutputDir $DataSource
$message = "Generate a quota report for $CustomerName"

Write-Host "Running deterministic multi-agent pipeline for $DataSource..."
uv run python -m src.orchestrator.multi_agent $message --customer $CustomerName --data-source $DataSource --output-dir $resolvedOutput

Write-Host "Artifacts written under $resolvedOutput"
