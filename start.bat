@echo off
REM CMD start script for DC Bot
REM Usage: start.bat

cd /d %~dp0

IF NOT EXIST .venv (
	python -m venv .venv
)

call .venv\Scripts\activate.bat

IF EXIST requirements.txt (
	pip install -r requirements.txt
)

REM Start the bot using package invocation
REM Start web backend in a new window
if exist .venv\Scripts\python.exe (
	start "DC Bot - Backend" .venv\Scripts\python.exe -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8000
) else (
	start "DC Bot - Backend" python -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8000
)

REM Start frontend (if node/npm available) in a new window
if exist web\frontend\package.json (
	start "DC Bot - Frontend" cmd /c "cd /d web\frontend && if not exist node_modules npm install && npm run dev -- --host 127.0.0.1"
)

REM Start the bot in this window
python -m src.mybot