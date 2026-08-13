#Requires -Version 5.1
<#
.SYNOPSIS
  Build, zip, and copy WorkforcePlanning publish output to the share folder.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\local-publish.ps1
#>
[CmdletBinding()]
param(
    [string]$Configuration = 'Release',
    [string]$Project = 'src/WorkforcePlanning.Api/WorkforcePlanning.Api.csproj',
    [string]$PublishDir = '.\artifacts\publish',
    [string]$ShareDir = 'C:\Users\tienlta\OneDrive - WIN\Project\weekly_workforce_planning\Deploy',
    [string]$ZipName = 'workforce_publish.zip'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$started = Get-Date
Write-Step "Repo: $RepoRoot"

$projectPath = Join-Path $RepoRoot $Project
if (-not (Test-Path -LiteralPath $projectPath)) {
    throw "Project not found: $projectPath"
}

$publishFull = if ([System.IO.Path]::IsPathRooted($PublishDir)) {
    $PublishDir
} else {
    Join-Path $RepoRoot $PublishDir
}

Write-Step "Clean publish dir: $publishFull"
if (Test-Path -LiteralPath $publishFull) {
    Remove-Item -LiteralPath $publishFull -Recurse -Force
}
New-Item -ItemType Directory -Path $publishFull -Force | Out-Null

Write-Step "dotnet publish ($Configuration)"
& dotnet publish $projectPath -c $Configuration -o $publishFull --no-self-contained
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE"
}

$artifactsDir = Split-Path -Parent $publishFull
if (-not (Test-Path -LiteralPath $artifactsDir)) {
    New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}

$zipPath = Join-Path $artifactsDir $ZipName
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Write-Step "Zip publish output -> $zipPath"
# Compress contents of publish folder (no extra parent folder level)
Push-Location $publishFull
try {
    Compress-Archive -Path * -DestinationPath $zipPath -Force
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $ShareDir)) {
    Write-Step "Create share dir: $ShareDir"
    New-Item -ItemType Directory -Path $ShareDir -Force | Out-Null
}

$destZip = Join-Path $ShareDir $ZipName
Write-Step "Copy zip -> $destZip"
Copy-Item -LiteralPath $zipPath -Destination $destZip -Force

$elapsed = (Get-Date) - $started
Write-Host ""
Write-Host "Local publish OK" -ForegroundColor Green
Write-Host "  Zip:      $destZip"
Write-Host "  Size:     $((Get-Item -LiteralPath $destZip).Length) bytes"
Write-Host "  Elapsed:  $([int]$elapsed.TotalSeconds)s"
