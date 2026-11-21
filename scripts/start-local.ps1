param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$bookkeepingRoot = Split-Path $PSScriptRoot -Parent
$bookkeepingPython = Join-Path $bookkeepingRoot '.venv/Scripts/python.exe'
$bookkeepingBackend = Join-Path $bookkeepingRoot 'backend'
$bookkeepingLogs = Join-Path $bookkeepingRoot '.local'
New-Item -ItemType Directory -Path $bookkeepingLogs -Force | Out-Null
if (-not (Test-Path -LiteralPath $bookkeepingPython)) { throw 'Create .venv and install backend/requirements.txt first.' }
if (-not (Test-Path -LiteralPath (Join-Path $bookkeepingBackend '.env'))) { throw 'Configure backend/.env first.' }

# This machine uses a dedicated instance, leaving the existing MySQL80 service intact.
if (-not (Get-NetTCPConnection -State Listen -LocalPort 33306 -ErrorAction SilentlyContinue)) {
    $bookkeepingMySQL = 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqld.exe'
    $bookkeepingData = Join-Path $env:LOCALAPPDATA 'Bookkeeping/mysql'
    if (-not (Test-Path -LiteralPath (Join-Path $bookkeepingData 'mysql'))) { throw 'The local project MySQL instance has not been initialized. See README.' }
    Start-Process -FilePath $bookkeepingMySQL -ArgumentList @('--no-defaults', "--datadir=$bookkeepingData", '--port=33306', '--bind-address=127.0.0.1', '--mysqlx=OFF', "--log-error=$bookkeepingData/server.log") -WindowStyle Hidden | Out-Null
    for ($bookkeepingAttempt = 0; $bookkeepingAttempt -lt 30; $bookkeepingAttempt++) {
        if (Get-NetTCPConnection -State Listen -LocalPort 33306 -ErrorAction SilentlyContinue) { break }
        Start-Sleep -Milliseconds 300
    }
}
Push-Location $bookkeepingBackend
try { & $bookkeepingPython -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' } }
finally { Pop-Location }

if (-not (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $bookkeepingPython -ArgumentList @("`"$(Join-Path $bookkeepingBackend 'run_server.py')`"") -WorkingDirectory $bookkeepingBackend -WindowStyle Hidden | Out-Null
}
for ($bookkeepingAttempt = 0; $bookkeepingAttempt -lt 30; $bookkeepingAttempt++) {
    try {
        $bookkeepingHealth = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
        if ($bookkeepingHealth.database -eq 'mysql') { break }
    } catch { Start-Sleep -Milliseconds 300 }
}
if ($bookkeepingHealth.database -ne 'mysql') { throw 'Web backend did not become ready; inspect .local/logs/app.log.' }
Write-Host 'Web: http://127.0.0.1:8000'
Write-Host 'Phone via USB: adb reverse tcp:8000 tcp:8000; server address http://127.0.0.1:8000'
if ($OpenBrowser) { Start-Process 'http://127.0.0.1:8000' }
