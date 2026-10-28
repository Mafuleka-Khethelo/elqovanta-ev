# Start a local PostgreSQL for ChargeConnect.
# Prefers Docker Compose. If Docker is not available, uses the PostgreSQL
# binaries under .tools and a data directory at .local\pgdata.
# Listens on 127.0.0.1:5432 only. This is a development database.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-PostgresPort {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", 5432, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne(500, $false)
        if (-not $ok) { return $false }
        $client.EndConnect($result)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

if (Test-PostgresPort) {
    Write-Host "PostgreSQL is already accepting connections on 127.0.0.1:5432."
    exit 0
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    Write-Host "Starting PostgreSQL with Docker Compose."
    docker compose up -d postgres
    exit $LASTEXITCODE
}

$Pgsql = Join-Path $Root ".tools\pgsql-src\pgsql"
$Share = Join-Path $Pgsql "share\postgres.bki"
$Zip = Join-Path $Root ".tools\installers\postgresql-16.15-5-windows-x64-binaries.zip"
if (-not (Test-Path $Share) -and (Test-Path $Zip)) {
    Write-Host "Extracting PostgreSQL binaries. The bin folder alone cannot initialise a database."
    Expand-Archive -Path $Zip -DestinationPath (Join-Path $Root ".tools\pgsql-src") -Force
}
$Bin = Join-Path $Pgsql "bin"
$Initdb = Join-Path $Bin "initdb.exe"
$PgCtl = Join-Path $Bin "pg_ctl.exe"
$Psql = Join-Path $Bin "psql.exe"
if (-not (Test-Path $Initdb)) {
    Write-Error "Docker is not available and PostgreSQL binaries were not found at $Bin."
}

$Data = Join-Path $Root ".local\pgdata"
$Log = Join-Path $Root ".local\pglog"
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

if (-not (Test-Path (Join-Path $Data "PG_VERSION"))) {
    Write-Host "Creating a local PostgreSQL data directory."
    & $Initdb -D $Data -U postgres -A trust -E UTF8 --locale=C --username=postgres
    Add-Content -Path (Join-Path $Data "postgresql.conf") -Value "listen_addresses = '127.0.0.1'"
    Add-Content -Path (Join-Path $Data "postgresql.conf") -Value "port = 5432"
}

Write-Host "Starting the local PostgreSQL server."
& $PgCtl -D $Data -l $Log start
$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Seconds 1
    & $Psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc "SELECT 1" | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
}
if (-not $ready) { Write-Error "PostgreSQL did not accept connections." }

function Invoke-PsqlValue([string]$Sql) {
    $value = & $Psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc $Sql
    if ($null -eq $value) { return "" }
    return ("$value").Trim()
}

$role = Invoke-PsqlValue "SELECT 1 FROM pg_roles WHERE rolname = 'chargeconnect'"
if ($role -ne "1") {
    & $Psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "CREATE ROLE chargeconnect LOGIN PASSWORD 'chargeconnect'"
}
$exists = Invoke-PsqlValue "SELECT 1 FROM pg_database WHERE datname = 'chargeconnect'"
if ($exists -ne "1") {
    & $Psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "CREATE DATABASE chargeconnect OWNER chargeconnect"
}
$testExists = Invoke-PsqlValue "SELECT 1 FROM pg_database WHERE datname = 'chargeconnect_test'"
if ($testExists -ne "1") {
    & $Psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "CREATE DATABASE chargeconnect_test OWNER chargeconnect"
}
Write-Host "Local PostgreSQL is ready on 127.0.0.1:5432."
