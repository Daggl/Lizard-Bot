#!/usr/bin/env pwsh
# PowerShell wrapper to run the Python start_all launcher
param()

Write-Host "Running start_all.py - starting bot and local UI in the current terminal"

# Prefer project's venv python if present
$venvPython = Join-Path -Path $PSScriptRoot -ChildPath ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
	Write-Host "Using venv python: $venvPython"
	# Force unbuffered output for Python processes
	$env:PYTHONUNBUFFERED = '1'
	& $venvPython -u start_all.py
} else {
	$env:PYTHONUNBUFFERED = '1'
	python -u start_all.py
}
