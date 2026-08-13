#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy WorkforcePlanning from share zip: stop App Pool, unzip overwrite, keep config, start App Pool.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\server-deploy.ps1
#>
[CmdletBinding()]
param(
    [string]$ShareDir = 'D:\Source publish\WorkforcePlanning_Tmp',
    [string]$ZipName = 'workforce_publish.zip',
    [string]$DeployPath = 'D:\WorkforcePlanning\WorkforcePublish',
    [string]$AppPoolName = 'WorkforcePlanningPool',
    [string[]]$KeepFiles = @('appsettings.json', 'web.config'),
    [int]$AppPoolTimeoutSec = 60
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-AppPoolState {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][ValidateSet('Started', 'Stopped')]$DesiredState,
        [int]$TimeoutSec = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        $state = (Get-WebAppPoolState -Name $Name).Value
        if ($state -eq $DesiredState) {
            return
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "App Pool '$Name' did not reach state '$DesiredState' within ${TimeoutSec}s (last: $state)."
}

$started = Get-Date
$zipPath = Join-Path $ShareDir $ZipName

Write-Step "Share zip: $zipPath"
if (-not (Test-Path -LiteralPath $zipPath)) {
    throw "Zip not found: $zipPath"
}

if (-not (Test-Path -LiteralPath $DeployPath)) {
    Write-Step "Create deploy path: $DeployPath"
    New-Item -ItemType Directory -Path $DeployPath -Force | Out-Null
}

Write-Step "Import WebAdministration"
Import-Module WebAdministration -ErrorAction Stop

Write-Step "Stop App Pool: $AppPoolName"
$pool = Get-Item "IIS:\AppPools\$AppPoolName" -ErrorAction SilentlyContinue
if (-not $pool) {
    throw "App Pool not found: $AppPoolName"
}

if ((Get-WebAppPoolState -Name $AppPoolName).Value -ne 'Stopped') {
    Stop-WebAppPool -Name $AppPoolName
    Wait-AppPoolState -Name $AppPoolName -DesiredState Stopped -TimeoutSec $AppPoolTimeoutSec
}
Write-Host "  App Pool stopped."

$backupRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("wp-deploy-cfg-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$backedUp = @()

try {
    Write-Step "Backup config files to $backupRoot"
    foreach ($name in $KeepFiles) {
        $src = Join-Path $DeployPath $name
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $backupRoot $name) -Force
            $backedUp += $name
            Write-Host "  Kept: $name"
        }
        else {
            Write-Host "  Skip (not present, will use zip): $name" -ForegroundColor Yellow
        }
    }

    $staging = Join-Path ([System.IO.Path]::GetTempPath()) ("wp-deploy-unzip-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    try {
        Write-Step "Expand zip to staging"
        Expand-Archive -LiteralPath $zipPath -DestinationPath $staging -Force

        Write-Step "Copy into deploy path (overwrite): $DeployPath"
        # Merge into existing folders. Do NOT use Copy-Item folder→existing-folder
        # (that creates nested wwwroot\wwwroot).
        & robocopy $staging $DeployPath /E /IS /IT /R:2 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
        # robocopy: 0-7 = success/partial; >=8 = failure
        if ($LASTEXITCODE -ge 8) {
            throw "robocopy failed with exit code $LASTEXITCODE"
        }
        $LASTEXITCODE = 0

        # Cleanup leftover nest from older buggy deploys
        $nestedWwwroot = Join-Path $DeployPath 'wwwroot\wwwroot'
        if (Test-Path -LiteralPath $nestedWwwroot) {
            Write-Step "Remove leftover nested folder: $nestedWwwroot"
            Remove-Item -LiteralPath $nestedWwwroot -Recurse -Force
        }
    }
    finally {
        if (Test-Path -LiteralPath $staging) {
            Remove-Item -LiteralPath $staging -Recurse -Force
        }
    }

    Write-Step "Restore config files"
    foreach ($name in $backedUp) {
        $bak = Join-Path $backupRoot $name
        $dest = Join-Path $DeployPath $name
        Copy-Item -LiteralPath $bak -Destination $dest -Force
        Write-Host "  Restored: $name"
    }
}
finally {
    if (Test-Path -LiteralPath $backupRoot) {
        Remove-Item -LiteralPath $backupRoot -Recurse -Force
    }
}

Write-Step "Start App Pool: $AppPoolName"
Start-WebAppPool -Name $AppPoolName
Wait-AppPoolState -Name $AppPoolName -DesiredState Started -TimeoutSec $AppPoolTimeoutSec
Write-Host "  App Pool started."

$elapsed = (Get-Date) - $started
Write-Host ""
Write-Host "Server deploy OK" -ForegroundColor Green
Write-Host "  DeployPath: $DeployPath"
Write-Host "  Zip:        $zipPath"
Write-Host "  Kept:       $($backedUp -join ', ')"
Write-Host "  AppPool:    $AppPoolName"
Write-Host "  Elapsed:    $([int]$elapsed.TotalSeconds)s"
