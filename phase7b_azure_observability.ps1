<#
.SYNOPSIS
    Phase 7B: Production-Safe Azure Observability Deployment for Juris AI (Hardened).
.DESCRIPTION
    Configures Azure Container Apps logging to Azure Log Analytics for Juris AI:
    - Preflight verification of active subscription (STOPS if not f739d65e-092c-4619-874d-db039016dc9f; no auto-switching).
    - Checks exit code and validates output for EVERY read-only preflight command.
    - Strictly STOPS if baseline production /health check fails or returns non-OK status.
    - Deep validation of existing workspace (subscription, resource group, region, SKU, quota, retention).
    - Checks $LASTEXITCODE after every Azure CLI command that creates or modifies resources.
    - Registers 'Microsoft.OperationalInsights' resource provider if NotRegistered.
    - Idempotently creates or updates 'log-juris-ai' workspace (0.1 GB/day cap, 30-day retention, uaenorth).
    - Reads back and asserts workspace region, daily quota, and retention after creation or update.
    - Retrieves workspace credentials securely into memory (never logged, displayed, or written to disk).
    - Updates 'env-juris-ai' logging destination in-place to 'log-analytics'.
    - Handles partial deployments safely: reports completed stages, never deletes resources or changes routing.
    - Verifies post-deployment environment configuration, /health endpoint, and log ingestion.
.PARAMETER SubscriptionId
    Target Azure Subscription ID (defaults to 'Azure for Students' f739d65e-092c-4619-874d-db039016dc9f).
.PARAMETER ResourceGroup
    Azure Resource Group name (defaults to 'rg-juris-ai').
.PARAMETER EnvironmentName
    Azure Container Apps environment name (defaults to 'env-juris-ai').
.PARAMETER AppName
    Azure Container App name (defaults to 'app-juris-ai').
.PARAMETER WorkspaceName
    Azure Log Analytics workspace name (defaults to 'log-juris-ai').
.PARAMETER Location
    Azure region for the workspace (defaults to 'uaenorth' to match the environment).
.PARAMETER DailyQuotaGb
    Ingestion cap in GB/day (defaults to 0.1 GB).
.PARAMETER RetentionDays
    Log retention period in days (defaults to 30 days).
.PARAMETER HealthEndpoint
    Production health check URL.
.PARAMETER Force
    Explicit operator switch to bypass interactive 'YES' confirmation prompt.
.EXAMPLE
    .\phase7b_azure_observability.ps1 -WhatIf
.EXAMPLE
    .\phase7b_azure_observability.ps1
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
    [string]$AppName = "app-juris-ai",

    [Parameter(Mandatory = $false)]
    [string]$WorkspaceName = "log-juris-ai",

    [Parameter(Mandatory = $false)]
    [string]$Location = "uaenorth",

    [Parameter(Mandatory = $false)]
    [double]$DailyQuotaGb = 0.1,

    [Parameter(Mandatory = $false)]
    [int]$RetentionDays = 30,

    [Parameter(Mandatory = $false)]
    [string]$HealthEndpoint = "https://app-juris-ai.calmflower-977aec4b.uaenorth.azurecontainerapps.io/health",

    [Parameter(Mandatory = $false)]
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Juris AI -- Phase 7B: Azure Observability Deployment Plan (Hardened)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Target Subscription ID : $SubscriptionId"
Write-Host "Resource Group         : $ResourceGroup"
Write-Host "Environment Name       : $EnvironmentName"
Write-Host "Container App Name     : $AppName"
Write-Host "Target Workspace Name  : $WorkspaceName"
Write-Host "Target Region          : $Location"
Write-Host "Daily Ingestion Cap    : $DailyQuotaGb GB/day"
Write-Host "Log Retention          : $RetentionDays days"
Write-Host "Health Probe Endpoint  : $HealthEndpoint"
Write-Host "=================================================================`n"

# In-memory holder for sensitive tokens to ensure guaranteed cleanup
$secWorkspaceKey = $null

# Stage tracking to support transparent partial-deployment reporting
$completedStages = [System.Collections.Generic.List[string]]::new()

try {
    # -------------------------------------------------------------------------
    # STAGE 0: PREFLIGHT CHECKS & DEEP VALIDATION (Strictly Read-Only)
    # -------------------------------------------------------------------------
    Write-Host "[Stage 0/5] Executing Preflight Checks & Validation..." -ForegroundColor Yellow

    # 1. Verify Azure CLI installed
    $azCmd = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azCmd) {
        throw "Azure CLI ('az') is not installed or not available in the current PATH."
    }
    Write-Host "  [+] Azure CLI executable detected." -ForegroundColor Green

    # 2. Verify Azure Context and Subscription (STOPS on mismatch; no auto-switching)
    Write-Host "  [*] Verifying currently active Azure subscription..."
    $currentAccountJson = az account show --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $currentAccountJson) {
        throw "Failed to retrieve active Azure account from Azure CLI (exit code: $LASTEXITCODE). Please run 'az login' first."
    }
    $currentAccount = $currentAccountJson | ConvertFrom-Json
    if ($currentAccount.id -ne $SubscriptionId) {
        throw "Active Azure subscription is '$($currentAccount.id)' ($($currentAccount.name)), but target subscription is '$SubscriptionId'. Automatic subscription switching is disabled for safety. Run 'az account set --subscription $SubscriptionId' manually and re-run."
    }
    Write-Host "  [+] Verified Active Subscription: $($currentAccount.name) ($($currentAccount.id))" -ForegroundColor Green

    # 3. Verify Resource Group exists
    Write-Host "  [*] Verifying Resource Group '$ResourceGroup'..."
    $rgJson = az group show --name $ResourceGroup --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $rgJson) {
        throw "Resource group '$ResourceGroup' was not found or failed to query in subscription '$SubscriptionId' (exit code: $LASTEXITCODE)."
    }
    $rg = $rgJson | ConvertFrom-Json
    Write-Host "  [+] Resource Group '$ResourceGroup' found (Location: $($rg.location), State: $($rg.properties.provisioningState))." -ForegroundColor Green

    # 4. Verify Container Apps Environment exists and inspect logging config
    Write-Host "  [*] Verifying Container Apps Environment '$EnvironmentName'..."
    $envJson = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $envJson) {
        throw "Container Apps Environment '$EnvironmentName' was not found or failed to query in '$ResourceGroup' (exit code: $LASTEXITCODE)."
    }
    $envObj = $envJson | ConvertFrom-Json
    $currentDest = $envObj.properties.appLogsConfiguration.destination
    if ([string]::IsNullOrEmpty($currentDest)) { $currentDest = "none (null)" }
    Write-Host "  [+] Environment '$EnvironmentName' exists." -ForegroundColor Green
    Write-Host "      Current logging destination: $currentDest" -ForegroundColor Gray
    Write-Host "      Provisioning state: $($envObj.properties.provisioningState)" -ForegroundColor Gray

    # 5. Verify Container App exists and is in healthy running state
    Write-Host "  [*] Verifying Container App '$AppName'..."
    $appJson = az containerapp show --resource-group $ResourceGroup --name $AppName --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $appJson) {
        throw "Container App '$AppName' was not found or failed to query in '$ResourceGroup' (exit code: $LASTEXITCODE)."
    }
    $appObj = $appJson | ConvertFrom-Json
    Write-Host "  [+] Container App '$AppName' found (Revision: $($appObj.properties.latestRevisionName), Status: $($appObj.properties.runningStatus))." -ForegroundColor Green

    # 6. Baseline /health probe (STOPS if unhealthy or non-OK)
    Write-Host "  [*] Probing baseline application health at $HealthEndpoint..."
    try {
        $baselineHealth = Invoke-RestMethod -Uri $HealthEndpoint -Method Get -TimeoutSec 15
        if ($null -eq $baselineHealth -or $baselineHealth.status -ne "ok") {
            throw "Baseline /health returned non-OK status: '$($baselineHealth.status)'."
        }
        Write-Host "  [+] Baseline /health probe successful (service: $($baselineHealth.service), version: $($baselineHealth.version))." -ForegroundColor Green
    } catch {
        throw "Baseline production /health check failed at '$HealthEndpoint': $($_.Exception.Message). Deployment halted to protect production service."
    }

    # 7. Check Resource Provider Registration
    Write-Host "  [*] Checking registration of 'Microsoft.OperationalInsights'..."
    $providerState = az provider show --namespace Microsoft.OperationalInsights --query registrationState -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($providerState)) {
        throw "Failed to query registration state for 'Microsoft.OperationalInsights' (exit code: $LASTEXITCODE)."
    }
    Write-Host "  [+] Microsoft.OperationalInsights status: $providerState" -ForegroundColor $(if ($providerState -eq "Registered") { "Green" } else { "Yellow" })

    # 8. Check Log Analytics Workspace existence & deep validate properties if existing
    Write-Host "  [*] Checking existence of Log Analytics workspace '$WorkspaceName'..."
    $wsListJson = az monitor log-analytics workspace list --resource-group $ResourceGroup --query "[?name=='$WorkspaceName']" --output json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $wsListJson) {
        throw "Failed to query Log Analytics workspace list in resource group '$ResourceGroup' (exit code: $LASTEXITCODE)."
    }
    $workspaceExists = $false
    $wsObj = $null
    $workspaceNeedsUpdate = $false

    $wsArray = $wsListJson | ConvertFrom-Json
    if ($wsArray.Count -gt 0) {
        $workspaceExists = $true
        $wsObj = $wsArray[0]

        Write-Host "  [+] Workspace '$WorkspaceName' already exists. Performing deep parameter validation:" -ForegroundColor Green

        # Validate Subscription ID in resource ID
        if ($wsObj.id -notmatch [regex]::Escape($SubscriptionId)) {
            throw "Existing workspace '$WorkspaceName' belongs to a different subscription than target '$SubscriptionId' (ID: $($wsObj.id))."
        }
        Write-Host "      [OK] Subscription ID verified in resource ID" -ForegroundColor Gray

        # Validate Resource Group in resource ID
        if ($wsObj.id -notmatch [regex]::Escape($ResourceGroup)) {
            throw "Existing workspace '$WorkspaceName' is in a different resource group than '$ResourceGroup' (ID: $($wsObj.id))."
        }
        Write-Host "      [OK] Resource Group verified in resource ID" -ForegroundColor Gray

        # Validate Region / Location
        $normWsLoc = ($wsObj.location -replace '\s','').ToLower()
        $normTargetLoc = ($Location -replace '\s','').ToLower()
        if ($normWsLoc -ne $normTargetLoc) {
            throw "Existing workspace '$WorkspaceName' is in region '$($wsObj.location)', which does not match target region '$Location'. Cross-region relocation is not supported."
        }
        Write-Host "      [OK] Region verified ($($wsObj.location))" -ForegroundColor Gray

        # Validate SKU
        $skuName = $wsObj.sku.name
        Write-Host "      [OK] Workspace SKU: $skuName" -ForegroundColor Gray

        # Validate Quota
        $existingQuota = [double]$wsObj.workspaceCapping.dailyQuotaGb
        Write-Host "      [*] Current Daily Quota: $existingQuota GB (Target: $DailyQuotaGb GB)" -ForegroundColor Gray
        if ($existingQuota -ne $DailyQuotaGb) {
            $workspaceNeedsUpdate = $true
            Write-Host "      [!] Workspace daily quota will be updated to $DailyQuotaGb GB." -ForegroundColor Yellow
        }

        # Validate Retention
        $existingRetention = [int]$wsObj.retentionInDays
        Write-Host "      [*] Current Retention: $existingRetention days (Target: $RetentionDays days)" -ForegroundColor Gray
        if ($existingRetention -ne $RetentionDays) {
            $workspaceNeedsUpdate = $true
            Write-Host "      [!] Workspace retention will be updated to $RetentionDays days." -ForegroundColor Yellow
        }

        Write-Host "      [OK] Workspace State: $($wsObj.provisioningState)" -ForegroundColor Gray
    }

    if (-not $workspaceExists) {
        Write-Host "  [-] Workspace '$WorkspaceName' does NOT exist yet (will be created in Stage 2)." -ForegroundColor Yellow
    }

    [void]$completedStages.Add("Stage 0: Preflight checks & deep parameter validation")
    Write-Host "`nAll Preflight Checks passed successfully." -ForegroundColor Green

    # -------------------------------------------------------------------------
    # MUTATION APPROVAL GATE
    # -------------------------------------------------------------------------
    Write-Host "`n=================================================================" -ForegroundColor Magenta
    Write-Host " [MUTATION NOTICE] The following changes will be applied to Azure:" -ForegroundColor Magenta
    if ($providerState -ne "Registered") {
        Write-Host "  1. [az provider register] Register provider 'Microsoft.OperationalInsights' on subscription." -ForegroundColor Magenta
    } else {
        Write-Host "  1. [az provider register] Skipped (provider already registered)." -ForegroundColor Gray
    }

    if (-not $workspaceExists) {
        Write-Host "  2. [az monitor log-analytics workspace create] Create workspace '$WorkspaceName' in '$Location' [Cap: $DailyQuotaGb GB/day, Retention: $RetentionDays days]." -ForegroundColor Magenta
    } elseif ($workspaceNeedsUpdate) {
        Write-Host "  2. [az monitor log-analytics workspace update] Update workspace '$WorkspaceName' to [Cap: $DailyQuotaGb GB/day, Retention: $RetentionDays days]." -ForegroundColor Magenta
    } else {
        Write-Host "  2. [az monitor log-analytics workspace] Workspace '$WorkspaceName' already compliant. No workspace update required." -ForegroundColor Gray
    }

    Write-Host "  3. [az containerapp env update] Update Container Apps Environment '$EnvironmentName' logging destination to 'log-analytics'." -ForegroundColor Magenta
    Write-Host "=================================================================`n" -ForegroundColor Magenta

    # Operator safety verification
    if ($PSCmdlet.ShouldProcess("Resource Group: $ResourceGroup", "Apply Azure Observability deployment")) {
        if (-not $Force) {
            $confirm = Read-Host "Type 'YES' to approve and execute these mutations"
            if ($confirm -ne 'YES') {
                Write-Host "Deployment aborted by operator. No resources were modified." -ForegroundColor Yellow
                return
            }
        } else {
            Write-Host "[-Force flag detected] Operator confirmation prompt bypassed via explicit -Force switch." -ForegroundColor Yellow
        }
    } else {
        Write-Host "WhatIf mode: stopping before any mutating actions." -ForegroundColor Yellow
        return
    }

    # -------------------------------------------------------------------------
    # STAGE 1: REGISTER RESOURCE PROVIDER (If required)
    # -------------------------------------------------------------------------
    if ($providerState -ne "Registered") {
        Write-Host "`n[Stage 1/5] Registering provider 'Microsoft.OperationalInsights'..." -ForegroundColor Cyan
        & az provider register --namespace Microsoft.OperationalInsights --wait
        if ($LASTEXITCODE -ne 0) {
            throw "Azure CLI failed with exit code $LASTEXITCODE while registering 'Microsoft.OperationalInsights'."
        }

        $providerState = az provider show --namespace Microsoft.OperationalInsights --query registrationState -o tsv
        if ($LASTEXITCODE -ne 0 -or $providerState -ne "Registered") {
            throw "Provider 'Microsoft.OperationalInsights' registration did not complete (State: $providerState, exit code: $LASTEXITCODE)."
        }
        Write-Host "  [+] Microsoft.OperationalInsights registered successfully." -ForegroundColor Green
    } else {
        Write-Host "`n[Stage 1/5] Provider 'Microsoft.OperationalInsights' is already registered. Skipping." -ForegroundColor Green
    }
    [void]$completedStages.Add("Stage 1: Resource provider Microsoft.OperationalInsights registered")

    # -------------------------------------------------------------------------
    # STAGE 2: CREATE OR CONFIGURE LOG ANALYTICS WORKSPACE
    # -------------------------------------------------------------------------
    if (-not $workspaceExists) {
        Write-Host "`n[Stage 2/5] Creating Log Analytics workspace '$WorkspaceName'..." -ForegroundColor Cyan
        Write-Host "      Location    : $Location" -ForegroundColor Gray
        Write-Host "      Daily Quota : $DailyQuotaGb GB" -ForegroundColor Gray
        Write-Host "      Retention   : $RetentionDays days" -ForegroundColor Gray

        & az monitor log-analytics workspace create `
            --resource-group $ResourceGroup `
            --workspace-name $WorkspaceName `
            --location $Location `
            --sku PerGB2018 `
            --retention-time $RetentionDays `
            --quota $DailyQuotaGb `
            --only-show-errors

        if ($LASTEXITCODE -ne 0) {
            throw "Azure CLI failed with exit code $LASTEXITCODE while creating workspace '$WorkspaceName'."
        }

        Write-Host "  [+] Workspace created." -ForegroundColor Green
    } else {
        Write-Host "`n[Stage 2/5] Verifying existing Log Analytics workspace '$WorkspaceName' parameters..." -ForegroundColor Cyan
        if ($workspaceNeedsUpdate) {
            Write-Host "  [*] Updating workspace retention to $RetentionDays days and quota to $DailyQuotaGb GB..." -ForegroundColor Yellow
            & az monitor log-analytics workspace update `
                --resource-group $ResourceGroup `
                --workspace-name $WorkspaceName `
                --retention-time $RetentionDays `
                --quota $DailyQuotaGb `
                --only-show-errors

            if ($LASTEXITCODE -ne 0) {
                throw "Azure CLI failed with exit code $LASTEXITCODE while updating workspace '$WorkspaceName'."
            }

            Write-Host "  [+] Workspace settings updated." -ForegroundColor Green
        } else {
            Write-Host "  [+] Existing workspace already matches target quota and retention." -ForegroundColor Green
        }
    }

    # Read back and strictly assert workspace region, daily quota, and retention
    Write-Host "  [*] Reading back and verifying workspace '$WorkspaceName' settings..."
    $verifiedWsJson = az monitor log-analytics workspace show --resource-group $ResourceGroup --workspace-name $WorkspaceName --output json
    if ($LASTEXITCODE -ne 0 -or -not $verifiedWsJson) {
        throw "Failed to read back workspace '$WorkspaceName' state after create/update (exit code: $LASTEXITCODE)."
    }
    $verifiedWs = $verifiedWsJson | ConvertFrom-Json
    if ($verifiedWs.provisioningState -ne "Succeeded") {
        throw "Workspace '$WorkspaceName' is in unexpected provisioning state: '$($verifiedWs.provisioningState)' (expected 'Succeeded')."
    }

    $readbackRegion = ($verifiedWs.location -replace '\s','').ToLower()
    $expectedRegion = ($Location -replace '\s','').ToLower()
    if ($readbackRegion -ne $expectedRegion) {
        throw "Workspace region verification failed: got '$($verifiedWs.location)', expected '$Location'."
    }

    $readbackQuota = [double]$verifiedWs.workspaceCapping.dailyQuotaGb
    if ($readbackQuota -ne $DailyQuotaGb) {
        throw "Workspace daily quota verification failed: got '$readbackQuota GB', expected '$DailyQuotaGb GB'."
    }

    $readbackRetention = [int]$verifiedWs.retentionInDays
    if ($readbackRetention -ne $RetentionDays) {
        throw "Workspace retention verification failed: got '$readbackRetention days', expected '$RetentionDays days'."
    }

    Write-Host "  [+] Verified read-back workspace properties:" -ForegroundColor Green
    Write-Host "      Provisioning State : $($verifiedWs.provisioningState)" -ForegroundColor Gray
    Write-Host "      Region             : $($verifiedWs.location)" -ForegroundColor Gray
    Write-Host "      Daily Quota        : $readbackQuota GB/day" -ForegroundColor Gray
    Write-Host "      Retention          : $readbackRetention days" -ForegroundColor Gray

    [void]$completedStages.Add("Stage 2: Log Analytics workspace $WorkspaceName verified/created")

    # -------------------------------------------------------------------------
    # STAGE 3: SECURE CREDENTIAL RETRIEVAL (In-Memory Only)
    # -------------------------------------------------------------------------
    Write-Host "`n[Stage 3/5] Retrieving Log Analytics workspace credentials in memory..." -ForegroundColor Cyan

    $workspaceCustomerId = az monitor log-analytics workspace show `
        --resource-group $ResourceGroup `
        --workspace-name $WorkspaceName `
        --query customerId -o tsv

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($workspaceCustomerId)) {
        throw "Failed to retrieve Customer ID for workspace '$WorkspaceName' (exit code: $LASTEXITCODE)."
    }

    # Primary key is retrieved strictly in memory; never printed, logged, or written to disk
    $secWorkspaceKey = az monitor log-analytics workspace get-shared-keys `
        --resource-group $ResourceGroup `
        --workspace-name $WorkspaceName `
        --query primarySharedKey -o tsv

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($secWorkspaceKey)) {
        throw "Failed to retrieve primary shared key for workspace '$WorkspaceName' (exit code: $LASTEXITCODE)."
    }

    Write-Host "  [+] Workspace Customer ID: $workspaceCustomerId" -ForegroundColor Green
    Write-Host "  [+] Primary shared key retrieved securely into memory (never displayed or written)." -ForegroundColor Green
    [void]$completedStages.Add("Stage 3: Workspace credentials securely retrieved in memory")

    # -------------------------------------------------------------------------
    # STAGE 4: UPDATE CONTAINER APPS ENVIRONMENT LOGGING
    # -------------------------------------------------------------------------
    Write-Host "`n[Stage 4/5] Updating Container Apps Environment '$EnvironmentName' logging destination..." -ForegroundColor Cyan
    Write-Host "  [*] Attaching workspace '$WorkspaceName' to '$EnvironmentName'..."

    & az containerapp env update `
        --name $EnvironmentName `
        --resource-group $ResourceGroup `
        --logs-destination log-analytics `
        --logs-workspace-id $workspaceCustomerId `
        --logs-workspace-key $secWorkspaceKey `
        --only-show-errors

    $envUpdateExitCode = $LASTEXITCODE

    # Immediately scrub sensitive token from memory and trigger garbage collection
    $secWorkspaceKey = $null
    [System.GC]::Collect()

    if ($envUpdateExitCode -ne 0) {
        throw "Azure CLI failed with exit code $envUpdateExitCode while updating '$EnvironmentName' logging destination."
    }

    Write-Host "  [+] Container Apps Environment updated to destination 'log-analytics'." -ForegroundColor Green
    [void]$completedStages.Add("Stage 4: Container Apps environment $EnvironmentName logging destination updated")

    # -------------------------------------------------------------------------
    # STAGE 5: POST-DEPLOYMENT VERIFICATION & HEALTH AUDIT
    # -------------------------------------------------------------------------
    Write-Host "`n[Stage 5/5] Performing Post-Deployment Verification..." -ForegroundColor Cyan

    # 1. Verify Environment AppLogsConfiguration
    $updatedEnvJson = az containerapp env show --resource-group $ResourceGroup --name $EnvironmentName --output json
    if ($LASTEXITCODE -ne 0 -or -not $updatedEnvJson) {
        throw "Failed to read back environment '$EnvironmentName' configuration (exit code: $LASTEXITCODE)."
    }
    $updatedEnv = $updatedEnvJson | ConvertFrom-Json
    $dest = $updatedEnv.properties.appLogsConfiguration.destination
    $configuredCustomerId = $updatedEnv.properties.appLogsConfiguration.logAnalyticsConfiguration.customerId
    Write-Host "  [+] Environment Logging Destination: $dest" -ForegroundColor Green
    Write-Host "  [+] Configured Customer ID         : $configuredCustomerId" -ForegroundColor Green

    if ($dest -ne "log-analytics" -or $configuredCustomerId -ne $workspaceCustomerId) {
        throw "Environment logging configuration does not match expected workspace customer ID ($configuredCustomerId != $workspaceCustomerId)."
    }

    # 2. Verify Application Routing and Live /health
    Write-Host "  [*] Testing production /health endpoint at $HealthEndpoint..."
    $postHealth = Invoke-RestMethod -Uri $HealthEndpoint -Method Get -TimeoutSec 15
    if ($null -eq $postHealth -or $postHealth.status -ne "ok") {
        Write-Warning "Health check returned unexpected status: $($postHealth.status)"
    } else {
        Write-Host "  [+] Live health check verified: status = 'ok', service = '$($postHealth.service)'." -ForegroundColor Green
    }

    # 3. Log Ingestion Verification
    Write-Host "`n  [*] Checking log ingestion pipeline..." -ForegroundColor Yellow
    Write-Host "      Note: Azure Log Analytics ingestion pipeline typically takes 1 to 3 minutes" -ForegroundColor Gray
    Write-Host "      for initial table generation and log ingestion (ContainerAppConsoleLogs_CL)." -ForegroundColor Gray

    try {
        $recentLogs = az monitor log-analytics query `
            --workspace $workspaceCustomerId `
            --analytics-query "ContainerAppConsoleLogs_CL | project TimeGenerated, ContainerAppName_s, Log_s | take 5" `
            --output table 2>$null

        if ($recentLogs) {
            Write-Host "  [+] Live Container App logs detected in Log Analytics:" -ForegroundColor Green
            $recentLogs | Write-Host
        } else {
            Write-Host "  [*] Ingestion pipeline is initializing. Run post-verification query after 2-3 minutes:" -ForegroundColor Yellow
            Write-Host ('      az monitor log-analytics query -w ' + $workspaceCustomerId + ' --analytics-query "ContainerAppConsoleLogs_CL | take 10" -o table') -ForegroundColor Cyan
        }
    } catch {
        Write-Host "  [*] Pipeline initializing. Tables will appear shortly after container activity." -ForegroundColor Gray
    }

    [void]$completedStages.Add("Stage 5: Post-deployment verification and live health audit")

    Write-Host "`n=================================================================" -ForegroundColor Green
    Write-Host " Observability Deployment Successfully Completed!" -ForegroundColor Green
    Write-Host " Workspace ID  : $workspaceCustomerId" -ForegroundColor Green
    Write-Host " Daily Cap     : $DailyQuotaGb GB/day" -ForegroundColor Green
    Write-Host " Retention     : $RetentionDays days" -ForegroundColor Green
    Write-Host " Container Env : $EnvironmentName [log-analytics]" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green

} catch {
    Write-Host "`n=================================================================" -ForegroundColor Red
    Write-Host " [DEPLOYMENT BLOCKED / HALTED] Stage Execution Summary:" -ForegroundColor Red
    Write-Host "=================================================================" -ForegroundColor Red
    Write-Host "Stages successfully completed before failure:" -ForegroundColor Yellow
    if ($completedStages.Count -gt 0) {
        foreach ($stage in $completedStages) {
            Write-Host "  [SUCCESS] $stage" -ForegroundColor Green
        }
    } else {
        Write-Host "  None (failed during initial preflight checks)." -ForegroundColor Gray
    }

    Write-Host "`nFailed operation details:" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Script trace: $($_.ScriptStackTrace)" -ForegroundColor DarkRed

    Write-Host "`nSafety and Integrity Guarantee:" -ForegroundColor Cyan
    Write-Host "  * No Azure resources were automatically deleted." -ForegroundColor Cyan
    Write-Host "  * No changes were made to production API routing, revisions, databases, or client apps." -ForegroundColor Cyan
    if ($completedStages -contains "Stage 4: Container Apps environment $EnvironmentName logging destination updated") {
        Write-Host "  * Stage 4 completed before the failure. To revert logging destination to 'none', run: .\phase7b_rollback_observability.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "  * Container environment logging destination was NOT modified. No rollback is required." -ForegroundColor Green
    }
    Write-Host "=================================================================`n" -ForegroundColor Red
} finally {
    if ($secWorkspaceKey) {
        $secWorkspaceKey = $null
        [System.GC]::Collect()
    }
}
