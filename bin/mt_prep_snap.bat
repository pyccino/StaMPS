@echo off
setlocal enabledelayedexpansion
rem StaMPS Windows shim: delegates to the Python port.
rem
rem setlocal enabledelayedexpansion is REQUIRED: %ERRORLEVEL% is expanded
rem at block-PARSE time, so `if (python -m ... & exit /b %ERRORLEVEL%)`
rem would always exit with the pre-call errorlevel. !ERRORLEVEL! expands
rem at runtime (delayed-expansion) so post-call errorlevel propagates.

set "STAMPS=%~dp0.."
for %%A in ("%STAMPS%") do set "STAMPS=%%~fA"
set "PATH=%STAMPS%\bin;%STAMPS%\external\snaphu\bin;%STAMPS%\external\triangle\bin;%PATH%"
set "PYTHONPATH=%STAMPS%\python;%PYTHONPATH%"

set "STAMPS_PYTHON="
if exist "%APPDATA%\PHASE\python.txt" set /p STAMPS_PYTHON=<"%APPDATA%\PHASE\python.txt"

if defined STAMPS_PYTHON (
    "%STAMPS_PYTHON%" -m stamps.mt_prep_snap %*
    exit /b !ERRORLEVEL!
)

rem Try `py -3` (python.org launcher) first.
where py >nul 2>&1
if !ERRORLEVEL! equ 0 (
    py -3 -m stamps.mt_prep_snap %*
    exit /b !ERRORLEVEL!
)

rem Fall back to plain `python` on PATH.
where python >nul 2>&1
if !ERRORLEVEL! equ 0 (
    python -m stamps.mt_prep_snap %*
    exit /b !ERRORLEVEL!
)

echo ERROR: No Python 3.11+ found. Install from https://www.python.org >&2
exit /b 9009
