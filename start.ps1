<#
PowerShell start script for DC Bot
Usage:
  ./start.ps1           # run in foreground
  ./start.ps1 -Detach   # run the bot in a detached/background process

This script:
- Creates a .venv virtual environment if missing
- Activates the venv in-session
- Installs requirements.txt if present
- Starts python -m src.mybot
#>

param(
    [switch]$Detach
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Output "Creating virtual environment (.venv)..."
    python -m venv .venv
}

Write-Output "Activating virtual environment..."
$activate = Join-Path $PWD ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    . $activate
} else {
    Write-Output "Warning: activate script not found: $activate"
}

if (Test-Path "requirements.txt") {
    Write-Output "Installing requirements..."
    pip install -r requirements.txt
} else {
    Write-Output "No requirements.txt found -- skipping install."
}

if ($Detach) {
    Write-Output "Starting bot in background..."
    $pythonPath = (Get-Command python).Source
    Start-Process -FilePath $pythonPath -ArgumentList '-m','src.mybot' -WorkingDirectory $root
    Write-Output "Bot started (detached)."
} else {
    Write-Output "Starting bot in foreground (press Ctrl+C to stop)..."
    & python -m src.mybot
}

# --- Start web backend and frontend when launching ---
# Start backend in a new window (detached)
function Start-Backend {
    if (Test-Path ".venv\Scripts\python.exe") {
        $pythonExe = Join-Path $PWD ".venv\Scripts\python.exe"
    } else {
        $pythonExe = "python"
    }
    Write-Output "Starting web backend in new window..."
    Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','web.backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $root
}

function Start-Frontend {
    if (Test-Path "web\frontend\package.json") {
        Write-Output "Starting frontend (will run npm install if needed) in new window..."
        Start-Process -FilePath "cmd.exe" -ArgumentList '/c','cd /d web\frontend && if not exist node_modules npm install && npm run dev -- --host 127.0.0.1' -WorkingDirectory (Join-Path $root 'web\frontend')
    } else {
        Write-Output "No frontend found at web\frontend — skipping frontend start."
    }
}

# If user requested detach, ensure backend/frontend also detached. If foreground run, start backend/frontend detached and keep bot foreground.
Start-Backend
Start-Frontend

