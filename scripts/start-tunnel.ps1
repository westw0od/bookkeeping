param([ValidateSet('http2', 'quic')][string]$Protocol = 'http2')
$ErrorActionPreference = 'Stop'
$bookkeepingRoot = (Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$bookkeepingState = Join-Path $bookkeepingRoot '.local/tunnel.json'
if (Test-Path -LiteralPath $bookkeepingState) {
    $bookkeepingTunnel = Get-Content -Raw -LiteralPath $bookkeepingState | ConvertFrom-Json
    $bookkeepingSupervisor = Get-CimInstance Win32_Process -Filter "ProcessId = $($bookkeepingTunnel.supervisor_pid)"
    if ($bookkeepingSupervisor -and $bookkeepingSupervisor.CommandLine -like "*$bookkeepingRoot*run-tunnel.py*") {
        Write-Host "Tunnel is running. Status: $bookkeepingState"
        if ($bookkeepingTunnel.url) { Write-Host $bookkeepingTunnel.url }
        return
    }
}
Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 5 | Out-Null
Start-Process -FilePath (Join-Path $bookkeepingRoot '.venv/Scripts/python.exe') -ArgumentList @("`"$(Join-Path $PSScriptRoot 'run-tunnel.py')`"", '--protocol', $Protocol) -WorkingDirectory $bookkeepingRoot -WindowStyle Hidden | Out-Null
Write-Host "Tunnel is starting. Status: $bookkeepingState"
Write-Host 'Temporary URLs change when a new tunnel is created. Keep this computer running.'
