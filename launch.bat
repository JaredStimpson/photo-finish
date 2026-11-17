@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  call "%~dp0setup.bat" --no-pause
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -c "import tkinter; import PIL"
if errorlevel 1 (
  call "%~dp0setup.bat" --no-pause
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :fail
echo Application closed. Press any key to close this window.
pause
exit /b 0
:fail
echo Launch failed. See the error above.
pause
exit /b 1
