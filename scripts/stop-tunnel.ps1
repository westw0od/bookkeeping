$ErrorActionPreference = 'Stop'
$bookkeepingRoot = (Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$bookkeepingStatePath = Join-Path $bookkeepingRoot '.local/tunnel.json'
if (-not (Test-Path -LiteralPath $bookkeepingStatePath)) { Write-Host 'No project tunnel is recorded.'; return }
$bookkeepingState = Get-Content -Raw -LiteralPath $bookkeepingStatePath | ConvertFrom-Json
$bookkeepingTargets = @()
foreach ($bookkeepingPair in @(@($bookkeepingState.supervisor_pid, 'run-tunnel.py'), @($bookkeepingState.pid, 'cloudflared.exe'))) {
    if (-not $bookkeepingPair[0]) { continue }
    $bookkeepingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($bookkeepingPair[0])"
    if (-not $bookkeepingProcess) { continue }
    if ($bookkeepingProcess.CommandLine -notlike "*$bookkeepingRoot*$($bookkeepingPair[1])*") { throw 'Recorded process is not this project tunnel. No process was stopped.' }
    $bookkeepingTargets += $bookkeepingProcess.ProcessId
}
foreach ($bookkeepingProcessId in $bookkeepingTargets) { Stop-Process -Id $bookkeepingProcessId }
$bookkeepingState.active = $false
$bookkeepingState | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $bookkeepingStatePath
Write-Host 'The project tunnel is stopped. Its temporary public address is no longer available.'
