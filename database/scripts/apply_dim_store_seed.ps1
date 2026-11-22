# Apply PLH dim_store seeds with UTF-8 so Vietnamese NVARCHAR literals are correct.
param(
    [string]$Server = "localhost\SQLEXPRESS",
    [string]$Database = "WorkforcePlanning"
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$dbDir = Join-Path $root "database"

if (-not (Get-Command sqlcmd -ErrorAction SilentlyContinue)) {
    throw "sqlcmd not found. Install SQL Server command-line tools."
}

$inputs = @(
    (Join-Path $dbDir "007_dim_store_seed.sql"),
    (Join-Path $dbDir "007_dim_store_detail_seed.sql")
)

foreach ($file in $inputs) {
    if (-not (Test-Path $file)) {
        throw "Missing $file. Run: python database\scripts\generate_dim_store_from_plh.py"
    }
    Write-Host "Running $file (UTF-8)..."
    sqlcmd -S $Server -d $Database -E -f 65001 -i $file
}

Write-Host "Done. Sample check:"
sqlcmd -S $Server -d $Database -E -f 65001 -Q "SELECT TOP 3 Code, Name, City FROM dbo.dim_store WHERE Code IN ('2005','2009','2017');"