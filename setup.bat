@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo Creating project virtual environment...
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -c "import tkinter; t = tkinter.Tk(); t.withdraw(); t.destroy()"
if errorlevel 1 (
  echo Python requires working Tcl/Tk support. Install or repair Python with Tcl/Tk enabled,
  echo then remove .venv and run setup.bat again.
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
echo Setup complete.
if /I not "%~1"=="--no-pause" pause
exit /b 0
:fail
echo Setup failed. See the error above.
if /I not "%~1"=="--no-pause" pause
exit /b 1
