@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   MHXX Save Editor - AI Research Platform
echo   http://127.0.0.1:8765
echo ============================================
echo.

REM ---- 1. locate a WORKING python ----
REM priority: WorkBuddy built-in (known good) > PATH python > py launcher
REM (PATH python may be a Store alias stub, so verify with --version)
set "PY="
if exist "%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe" set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if defined PY goto :verify_py
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :verify_py
where py >nul 2>nul
if not errorlevel 1 set "PY=py"
if defined PY goto :verify_py
goto :no_py

:verify_py
"%PY%" --version >nul 2>&1
if errorlevel 1 goto :verify_failed
goto :found_py

:verify_failed
if "%PY%"=="py" goto :no_py
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py"
if defined PY goto :verify_py
goto :no_py

:found_py
echo [Python] %PY%
goto :step2

:no_py
echo [ERROR] No working Python found. Install Python 3.10+ and add it to PATH.
pause
exit /b 1

:step2
REM ---- 2. already running? ----
curl -s --max-time 2 http://127.0.0.1:8765/api/health >nul 2>&1
if errorlevel 1 goto :not_running
echo [INFO] Platform already running. Opening browser...
start "" "http://127.0.0.1:8765"
pause
exit /b 0

:not_running
REM ---- 3. extract data tables if missing ----
if exist "data\offsets.json" goto :have_data
echo [INIT] Data files missing, extracting from C# source...
"%PY%" tools\extract.py
if errorlevel 1 goto :extract_failed
:have_data

REM ---- 4. start server in background, then open browser ----
echo [START] Starting platform server...
start "" /b %PY% webapp\server.py --port 8765 > "%TEMP%\mhxx_server.log" 2>&1
timeout /t 2 /nobreak >nul 2>&1
start "" "http://127.0.0.1:8765"
echo [DONE] Server started. Close this window to stop it.
echo        Log: %TEMP%\mhxx_server.log
echo.
pause
exit /b 0

:extract_failed
echo [ERROR] Data extraction failed. Check MHXXSaveEditor\Data\ source files.
pause
exit /b 1
