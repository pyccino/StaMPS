@echo off
setlocal enabledelayedexpansion
rem StaMPS Windows shim: delegates to the Python port.
rem See mt_prep_snap.bat for design notes.

set "STAMPS=%~dp0.."
for %%A in ("%STAMPS%") do set "STAMPS=%%~fA"
set "PATH=%STAMPS%\bin;%STAMPS%\external\snaphu\bin;%STAMPS%\external\triangle\bin;%PATH%"
set "PYTHONPATH=%STAMPS%\python;%PYTHONPATH%"

set "STAMPS_PYTHON="
if exist "%APPDATA%\PHASE\python.txt" set /p STAMPS_PYTHON=<"%APPDATA%\PHASE\python.txt"

set "PYTHON_EXE="
if defined STAMPS_PYTHON (
    set PYTHON_EXE="!STAMPS_PYTHON!"
    goto :check_stub
)

where py >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py -3"
    goto :check_stub
)

where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    goto :check_stub
)

echo ERROR: No Python 3.11+ found. Install from https://www.python.org >&2
exit /b 9009

:check_stub
for /f "tokens=*" %%i in ('%PYTHON_EXE% -c "import sys; print(sys.executable)" 2^>nul') do set RESOLVED_PY=%%i
if "!RESOLVED_PY!"=="" (
    echo ERROR: Python launcher at "!PYTHON_EXE!" failed to run "import sys". >&2
    echo This is typically the Microsoft Store stub. Install real Python 3.11+ from https://www.python.org. >&2
    exit /b 9
)
echo !RESOLVED_PY! | findstr /I "\\WindowsApps\\" >nul
if !errorlevel! equ 0 (
    echo ERROR: "!RESOLVED_PY!" is the Microsoft Store Python stub. >&2
    echo Install real Python 3.11+ from https://www.python.org and ensure it's ahead on PATH. >&2
    exit /b 9
)

%PYTHON_EXE% -m stamps.mt_extract_cands %*
exit /b !errorlevel!
