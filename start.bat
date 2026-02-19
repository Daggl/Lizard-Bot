@echo off
REM CMD start script for DC Bot
REM Usage: start.bat

cd /d %~dp0














python bot.py
necho Starting bot...)  echo No requirements.txt found — skipping install.) ELSE (  pip install -r requirements.txt  echo Installing requirements...
nIF EXIST requirements.txt (
ncall .venv\Scripts\activate.bat)  python -m venv .venv  echo Creating virtual environment...nIF NOT EXIST .venv (