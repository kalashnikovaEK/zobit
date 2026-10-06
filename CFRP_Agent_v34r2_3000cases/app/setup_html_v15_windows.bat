@echo off
rem [NEW v18] Python 3.14 Windows installation profile.
rem [NEW v15] HTML-only installation; no Streamlit.
cd /d "%~dp0"
py -3.14 --version >nul 2>&1
if errorlevel 1 (
 echo Python 3.14 is required. Install it alongside your existing Python.
 pause
 exit /b 1
)
py -3.14 -m venv .venv_windows_py314_v18
if errorlevel 1 goto failed
.venv_windows_py314_v18\Scripts\python.exe -m pip install -r requirements-windows-py314-v18.txt
if errorlevel 1 goto failed
rem [NEW v17] Runtime checker probes Numba safely and keeps diagnostics.
.venv_windows_py314_v18\Scripts\python.exe check_html_runtime_v15.py > runtime_check_v18.log 2>&1
rem [NEW v17] Capture checker status before displaying the log.
set "CFRP_CHECK_STATUS=%errorlevel%"
type runtime_check_v18.log
if not "%CFRP_CHECK_STATUS%"=="0" goto failed
echo Ready. Run run_html_v15_windows.bat
pause
exit /b 0
:failed
echo Setup failed. Read the error above.
pause
exit /b 1
