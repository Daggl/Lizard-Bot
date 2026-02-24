#!/usr/bin/env pwsh
# PowerShell wrapper to run the Python start_all launcher
param()

Write-Host "Running start_all.py - starting bot and local UI in the current terminal"

# Prefer project's venv python if present
$venvPython = Join-Path -Path $PSScriptRoot -ChildPath ".venv\Scripts\python.exe"
try {
	# Ensure a virtualenv exists and requirements are installed
	if (-not (Test-Path $venvPython)) {
		Write-Host "Virtual environment not found. Creating .venv..."
		& python -m venv .venv
	}

	if (Test-Path $venvPython) {
		Write-Host "Using venv python: $venvPython"
		Write-Host "Ensuring requirements from requirements.txt are installed..."
		& $venvPython -m pip install -r requirements.txt
		# Force unbuffered output for Python processes
		$env:PYTHONUNBUFFERED = '1'
		& $venvPython -u start_all.py
	} else {
		Write-Host "No usable python found in .venv and system python failed to create venv. Falling back to system python."
		$env:PYTHONUNBUFFERED = '1'
		python -u start_all.py
	}
} catch {
	Write-Host "Error preparing environment: $_"
	Write-Host "Attempting to run start_all.py with system python anyway..."
	$env:PYTHONUNBUFFERED = '1'
	python -u start_all.py
}
