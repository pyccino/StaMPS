@echo off
setlocal enabledelayedexpansion

rem Resolve STAMPS from this script's location
set "STAMPS=%~dp0.."
for %%A in ("%STAMPS%") do set "STAMPS=%%~fA"

rem Prepend paths
set "PATH=%STAMPS%\bin;%STAMPS%\external\snaphu\bin;%STAMPS%\external\triangle\bin;%PATH%"
set "PYTHONPATH=%STAMPS%\python;%PYTHONPATH%"

rem Resolve Python to an ABSOLUTE PATH (needed for stub detection below).
rem Preference order: shared PHASE config, py launcher, python3 on PATH, python on PATH.
set "STAMPS_PYTHON="
if exist "%APPDATA%\PHASE\python.txt" (
    set /p STAMPS_PYTHON=<"%APPDATA%\PHASE\python.txt"
)
if not defined STAMPS_PYTHON (
    for /f "tokens=*" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "STAMPS_PYTHON=%%i"
)
if not defined STAMPS_PYTHON (
    for /f "delims=" %%P in ('where python3 2^>nul') do (
        if not defined STAMPS_PYTHON set "STAMPS_PYTHON=%%P"
    )
)
if not defined STAMPS_PYTHON (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined STAMPS_PYTHON set "STAMPS_PYTHON=%%P"
    )
)
if not defined STAMPS_PYTHON (
    echo ERROR: No Python 3.11+ found. Install from https://www.python.org or set STAMPS_PYTHON. >&2
    exit /b 9009
)

rem Detect Microsoft Store stub:
rem (a) path fragment \WindowsApps\ is where Store stubs live;
rem (b) verify we can actually import sys (Store stub opens the Store instead).
echo "%STAMPS_PYTHON%" | findstr /L /I "\WindowsApps\" >nul
if %ERRORLEVEL%==0 (
    echo ERROR: "%STAMPS_PYTHON%" is the Microsoft Store Python stub. Install real Python from python.org. >&2
    exit /b 9009
)
"%STAMPS_PYTHON%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo ERROR: "%STAMPS_PYTHON%" cannot execute Python (likely a Store stub or broken install). >&2
    exit /b 9009
)

"%STAMPS_PYTHON%" -m stamps.mt_extract_cands %*
exit /b %ERRORLEVEL%
