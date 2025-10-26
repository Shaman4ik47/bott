@echo off
setlocal

rem Determine project directory as the directory of this script
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%" || exit /b 1

rem Load BOT_TOKEN from file if present (first line)
if exist "BOT_TOKEN.txt" (
  for /f "usebackq delims=" %%A in ("BOT_TOKEN.txt") do (
    set "BOT_TOKEN=%%A"
    goto :token_loaded
  )
)
:token_loaded

rem Ensure virtual environment exists and dependencies are installed
if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating virtual environment...
  py -3 -m venv .venv || exit /b 1
  echo [setup] Upgrading pip and installing requirements...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt >nul 2>&1
)

rem Start the bot and append stdout/stderr to log
echo [start] Launching bot... >> "%PROJECT_DIR%\bot.log"
".venv\Scripts\python.exe" -u main.py >> "%PROJECT_DIR%\bot.log" 2>&1

endlocal

