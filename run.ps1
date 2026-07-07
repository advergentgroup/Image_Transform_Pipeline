$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim()
        if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path "env:$name" -Value $value
    }
}

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "Created .env from .env.example"
    } else {
        Write-Warning ".env not found - create it from .env.example"
    }
}

Import-DotEnv $EnvFile

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
    $pidList = $pids -join ", "
    Write-Warning "Port $port is already in use (PID(s): $pidList)."
    Write-Warning "Stop old servers with Ctrl+C, or run: Stop-Process -Id $pidList -Force"
    exit 1
}

& $VenvPython app.py @args
