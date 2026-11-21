# Run manually when the current local server needs to load code changes.
$ErrorActionPreference = 'Stop'
$bookkeepingRoot = (Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$bookkeepingBackend = Join-Path $bookkeepingRoot 'backend'
$bookkeepingListeners = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)
$bookkeepingProcessIds = @($bookkeepingListeners | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($bookkeepingProcessId in $bookkeepingProcessIds) {
    $bookkeepingServer = Get-CimInstance Win32_Process -Filter "ProcessId = $bookkeepingProcessId"
    $bookkeepingKnownCommand = $bookkeepingServer -and ($bookkeepingServer.CommandLine -like '*uvicorn main:app*' -or $bookkeepingServer.CommandLine -like '*run_server.py*')
    if (-not $bookkeepingServer -or $bookkeepingServer.Name -notmatch '^python(w)?\.exe$' -or -not $bookkeepingKnownCommand -or
        $bookkeepingServer.CommandLine.IndexOf($bookkeepingBackend, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'Port 8000 belongs to a different application. No process was stopped.'
    }
}
foreach ($bookkeepingProcessId in $bookkeepingProcessIds) { Stop-Process -Id $bookkeepingProcessId }
for ($bookkeepingAttempt = 0; $bookkeepingAttempt -lt 30; $bookkeepingAttempt++) {
    if (-not (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 200
}
if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) { throw 'Port 8000 is still in use.' }
& (Join-Path $PSScriptRoot 'start-local.ps1')
