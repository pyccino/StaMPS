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

if defined STAMPS_PYTHON (
    "%STAMPS_PYTHON%" -m stamps.mt_extract_cands %*
    exit /b !ERRORLEVEL!
)

where py >nul 2>&1
if !ERRORLEVEL! equ 0 (
    py -3 -m stamps.mt_extract_cands %*
    exit /b !ERRORLEVEL!
)

where python >nul 2>&1
if !ERRORLEVEL! equ 0 (
    python -m stamps.mt_extract_cands %*
    exit /b !ERRORLEVEL!
)

echo ERROR: No Python 3.11+ found. Install from https://www.python.org >&2
exit /b 9009
