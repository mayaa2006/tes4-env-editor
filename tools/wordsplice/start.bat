@echo off
rem Word Splicer launcher: sets itself up the first time, then opens the screen.
rem Usage: start.bat --lines "C:\path\to\swap\splice"   (extra options are passed through)
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is needed. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up. This downloads about 150 MB and takes a few minutes.
  python -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)
".venv\Scripts\python.exe" -m wordsplice %*
if errorlevel 1 pause
exit /b 0
:fail
echo Setup failed. See the messages above.
pause
exit /b 1
