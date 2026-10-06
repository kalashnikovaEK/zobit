@echo off
rem [NEW v18] Python 3.14 Windows installation profile.
rem [NEW v15] Integrated HTML dashboard.
cd /d "%~dp0"
if not exist .venv_windows_py314_v18\Scripts\python.exe (
 echo Run setup_html_v15_windows.bat first.
 pause
 exit /b 1
)
.venv_windows_py314_v18\Scripts\python.exe check_html_runtime_v15.py
if errorlevel 1 (
 pause
 exit /b 1
)
.venv_windows_py314_v18\Scripts\python.exe interactive_server.py
pause
