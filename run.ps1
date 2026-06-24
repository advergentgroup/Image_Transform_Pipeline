$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python 3.12 virtualenv..."
    py -3.12 -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python 3.12 is required for vtracer. Install from https://www.python.org/downloads/"
    }
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
}

Write-Host "Starting app with $VenvPython"
Set-Location $Root

$port = if ($env:PORT) { [int]$env:PORT } else { 5000 }
$listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $pids = $listeners.OwningProcess | Sort-Object -Unique
    Write-Warning "Port $port is already in use (PID(s): $($pids -join ', '))."
    Write-Warning "Stop old servers with Ctrl+C, or: Stop-Process -Id $($pids -join ',') -Force"
    exit 1
}

& $VenvPython app.py @args
