<#
.SYNOPSIS
    Rollback Script for Juris AI Azure Observability (Phase 7B - Hardened).
.DESCRIPTION
    Safely reverts the Container Apps Environment 'env-juris-ai' logging destination
    back to 'none' without deleting the Log Analytics workspace or any historical logs.
    - Preflight verification of active subscription (STOPS if not f739d65e-092c-4619-874d-db039016dc9f; no auto-switching).
    - Checks exit code and validates output for read-only preflight commands.
    - Reverts 'env-juris-ai' logging destination in-place to 'none'.
    - Checks $LASTEXITCODE and halts immediately on error.
    - Reads back the actual environment logging configuration and asserts destination is 'none'.
    - Validates production API /health endpoint.
    - Leaves 'log-juris-ai' workspace and ingested logs untouched for audit integrity.
.PARAMETER SubscriptionId
    Target Azure Subscription ID (defaults to 'f739d65e-092c-4619-874d-db039016dc9f').
.PARAMETER ResourceGroup
    Azure Resource Group name (defaults to 'rg-juris-ai').
.PARAMETER EnvironmentName
    Azure Container Apps environment name (defaults to 'env-juris-ai').
.PARAMETER HealthEndpoint
    Production health check URL.
.PARAMETER Force
    Explicit operator switch to bypass interactive 'YES' confirmation prompt.
.EXAMPLE
    .\phase7b_rollback_observability.ps1 -WhatIf
.EXAMPLE
    .\phase7b_rollback_observability.ps1
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [string]$SubscriptionId = "f739d65e-092c-4619-874d-db039016dc9f",

    [Parameter(Mandatory = $false)]
    [string]$ResourceGroup = "rg-juris-ai",

    [Parameter(Mandatory = $false)]
    [string]$EnvironmentName = "env-juris-ai",

    [Parameter(Mandatory = $false)]
    [string]$HealthEndpoint = "https://app-juris-ai.calmflower-977aec4b.uaenorth.azurecontainerapps.io/health",

    [Parameter(Mandatory = $false)]
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host " Juris AI -- Phase 7B: Azure Observability Rollback Plan (Hardened)" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host "Target Subscription ID : $SubscriptionId"
Write-Host "Resource Group         : $ResourceGroup"
Write-Host "Environment Name       : $EnvironmentName"
Write-Host "Action                 : Revert logging destination to 'none'"
Write-Host "Preservation Policy    : Workspace & historical data will NOT be deleted"
Write-Host "=================================================================`n"

try {
    # 1. Verify Azure CLI and account
    Write-Host "[Stage 0/3] Executing Rollback Preflight Checks..." -ForegroundColor Yellow
    $azCmd = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azCmd) {
        throw "Azure CLI ('az') is not installed or not available in the current PATH."
    }

    # Verify currently active subscription (STOPS on mismatch; no auto-switching)
    $currentAccountJson = az account show --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $currentAccountJson) {
        throw "Failed to retrieve active Azure account from Azure CLI (exit code: $LASTEXITCODE). Run 'az login' first."
    }
    $currentAccount = $currentAccountJson | ConvertFrom-Json
    if ($currentAccount.id -ne $SubscriptionId) {
        throw "Active Azure subscription is '$($currentAccount.id)' ($($currentAccount.name)), but target subscription is '$SubscriptionId'. Automatic subscription switching is disabled for safety. Run 'az account set --subscription $SubscriptionId' manually and re-run."
    }
    Write-Host "  [+] Verified Active Subscription: $($currentAccount.name) ($($currentAccount.id))" -ForegroundColor Green

    # 2. Inspect current environment state
    Write-Host "  [*] Inspecting Container Apps Environment '$EnvironmentName'..."
    $envJson = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $envJson) {
        throw "Environment '$EnvironmentName' not found or failed to query in '$ResourceGroup' (exit code: $LASTEXITCODE)."
    }
    $envObj = $envJson | ConvertFrom-Json
    $currentDest = $envObj.properties.appLogsConfiguration.destination
    if ([string]::IsNullOrEmpty($currentDest)) { $currentDest = "none (null)" }
    Write-Host "  [+] Current logging destination: $currentDest" -ForegroundColor Cyan

    if ($currentDest -eq "none (null)" -or $currentDest -eq "none") {
        Write-Host "Logging destination is already 'none'. No rollback needed." -ForegroundColor Green
        return
    }

    # -------------------------------------------------------------------------
    # ROLLBACK MUTATION GATE
    # -------------------------------------------------------------------------
    Write-Host "`n=================================================================" -ForegroundColor Magenta
    Write-Host " [MUTATION NOTICE] Rollback will apply the following change:" -ForegroundColor Magenta
    Write-Host "  1. [az containerapp env update] Revert '$EnvironmentName' logging destination to 'none'." -ForegroundColor Magenta
    Write-Host "  2. Workspace and existing historical telemetry will remain preserved." -ForegroundColor Magenta
    Write-Host "=================================================================`n" -ForegroundColor Magenta

    if ($PSCmdlet.ShouldProcess("Environment: $EnvironmentName", "Revert logging destination to 'none'")) {
        if (-not $Force) {
            $confirm = Read-Host "Type 'YES' to approve reverting logging destination to 'none'"
            if ($confirm -ne 'YES') {
                Write-Host "Rollback aborted by operator. No resources were modified." -ForegroundColor Yellow
                return
            }
        } else {
            Write-Host "[-Force flag detected] Operator confirmation prompt bypassed via explicit -Force switch." -ForegroundColor Yellow
        }
    } else {
        Write-Host "WhatIf mode: stopping before rollback." -ForegroundColor Yellow
        return
    }

    # -------------------------------------------------------------------------
    # STAGE 1: EXECUTE REVERT COMMAND
    # -------------------------------------------------------------------------
    Write-Host "`n[Stage 1/2] Reverting logging destination for '$EnvironmentName' to 'none'..." -ForegroundColor Cyan
    & az containerapp env update `
        --name $EnvironmentName `
        --resource-group $ResourceGroup `
        --logs-destination none `
        --only-show-errors

    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed with exit code $LASTEXITCODE during rollback 'az containerapp env update'."
    }
    Write-Host "  [+] Environment logging revert command executed successfully." -ForegroundColor Green

    # -------------------------------------------------------------------------
    # STAGE 2: POST-ROLLBACK VERIFICATION
    # -------------------------------------------------------------------------
    Write-Host "`n[Stage 2/2] Performing Post-Rollback Verification..." -ForegroundColor Cyan

    # Read back the actual configuration and assert destination is none
    $revertedEnvJson = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json
    if ($LASTEXITCODE -ne 0 -or -not $revertedEnvJson) {
        throw "Failed to read back Container Apps Environment configuration after rollback update (exit code: $LASTEXITCODE)."
    }
    $revertedEnv = $revertedEnvJson | ConvertFrom-Json
    $newDest = $revertedEnv.properties.appLogsConfiguration.destination

    if (-not [string]::IsNullOrEmpty($newDest) -and $newDest -ne "none") {
        throw "Rollback verification failed: environment logging destination is '$newDest', expected 'none' or null."
    }
    Write-Host "  [+] Verified read-back logging destination: $(if ([string]::IsNullOrEmpty($newDest)) { 'none (null)' } else { $newDest })" -ForegroundColor Green

    # Verify live production health endpoint
    Write-Host "  [*] Verifying live /health endpoint at $HealthEndpoint..."
    try {
        $health = Invoke-RestMethod -Uri $HealthEndpoint -Method Get -TimeoutSec 15
        if ($null -eq $health -or $health.status -ne "ok") {
            Write-Warning "Health check returned unexpected status: $($health.status)"
        } else {
            Write-Host "  [+] Health check verified: status = '$($health.status)', service = '$($health.service)'." -ForegroundColor Green
        }
    } catch {
        Write-Warning "Health probe failed: $($_.Exception.Message)"
    }

    Write-Host "`n=================================================================" -ForegroundColor Green
    Write-Host " Rollback Completed Successfully." -ForegroundColor Green
    Write-Host " Environment '$EnvironmentName' logging destination: none" -ForegroundColor Green
    Write-Host " Historical logs in 'log-juris-ai' have been preserved." -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green

} catch {
    Write-Host "`n=================================================================" -ForegroundColor Red
    Write-Host " [FATAL ERROR] Rollback encountered an error:" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Script trace: $($_.ScriptStackTrace)" -ForegroundColor DarkRed
    Write-Host "`nSafety and Integrity Guarantee:" -ForegroundColor Cyan
    Write-Host "  * No Azure resources were automatically deleted." -ForegroundColor Cyan
    Write-Host "  * No changes were made to production API routing, revisions, databases, or client apps." -ForegroundColor Cyan
    Write-Host "=================================================================`n" -ForegroundColor Red
}
