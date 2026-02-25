@echo off
echo Running start_all.py - starting bot and local UI in this terminal

REM Prefer project's venv python if present
set VENV_PY=%~dp0\.venv\Scripts\python.exe

REM If venv missing, try to create it
if not exist "%VENV_PY%" (
  echo Virtual environment not found. Creating .venv...
  python -m venv "%~dp0\.venv"
)

if exist "%VENV_PY%" (
  echo Using venv python: %VENV_PY%
  echo Ensuring requirements from requirements.txt are installed...
  "%VENV_PY%" -m pip install -r "%~dp0\requirements.txt"
  set PYTHONUNBUFFERED=1
  "%VENV_PY%" -u "%~dp0\start_all.py"
) else (
  echo No venv available; falling back to system python
  set PYTHONUNBUFFERED=1
  python -u "%~dp0\start_all.py"
)
