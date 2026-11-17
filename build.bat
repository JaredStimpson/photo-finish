@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  call "%~dp0setup.bat" --no-pause
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -c "import tkinter; import PIL; import PyInstaller"
if errorlevel 1 (
  call "%~dp0setup.bat" --no-pause
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name photo-finish --paths "%~dp0" --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0" "%~dp0main.py"
if errorlevel 1 goto :fail
if not exist "%~dp0dist\photo-finish.exe" goto :fail
echo Built "%~dp0dist\photo-finish.exe"
pause
exit /b 0
:fail
echo Build failed. See the error above.
pause
exit /b 1
