@echo off
rem [NEW v18] Python 3.14 Windows installation profile.
rem [NEW v17] One Windows entry point: install, check, start.
setlocal
cd /d "%~dp0"
rem [NEW v30] Apply incoming organized runtime path while preserving current UI.
if exist "%~dp0app\windows_launcher_v17.py" cd /d "%~dp0app"
py -3.14 --version >nul 2>&1
if not errorlevel 1 (
    py -3.14 windows_launcher_v17.py
    goto finished
)
python --version >nul 2>&1
if not errorlevel 1 (
    python windows_launcher_v17.py
    goto finished
)
echo Python 3.14 is required. Install Python 3.14 and enable the Python launcher.
:finished
rem [NEW v17] Keep all setup/runtime failure messages visible.
pause
endlocal
