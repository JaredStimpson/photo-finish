@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  call "%~dp0setup.bat"
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -c "import tkinter; import PIL"
if errorlevel 1 (
  call "%~dp0setup.bat"
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto :fail
exit /b 0
:fail
echo Launch failed. See the error above.
pause
exit /b 1
