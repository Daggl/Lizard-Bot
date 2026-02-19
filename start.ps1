<#
PowerShell start script for DC Bot
Usage:
  ./start.ps1           # run in foreground
  ./start.ps1 -Detach   # run the bot in a detached/background process

Behavior:
- Creates a `.venv` virtual environment if missing
- Activates the venv in-session
- Installs `requirements.txt` if present
- Starts `bot.py`
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
. $activate

if (Test-Path "requirements.txt") {
    Write-Output "Installing requirements..."
    pip install -r requirements.txt
} else {
    Write-Output "No requirements.txt found — skipping install."
}

if ($Detach) {
    Write-Output "Starting bot in background..."
    $pythonPath = (Get-Command python).Source
    Start-Process -FilePath $pythonPath -ArgumentList "bot.py" -WorkingDirectory $root
    Write-Output "Bot started (detached)."
} else {
    Write-Output "Starting bot in foreground (press Ctrl+C to stop)..."
    python bot.py
}
