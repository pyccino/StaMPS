@echo off
rem StaMPS Windows shim: delegates to the Python port.
rem
rem Resolve STAMPS root from this script's location, configure env, and
rem invoke `py -3 -m stamps.mt_prep_snap`. The `py` launcher is standard
rem on Windows installs of Python from python.org.
rem
rem Deliberately minimal cmd.exe logic: no nested `if (...)` blocks, no
rem `for /f` with parenthesized Python commands. Both are fragile — the
rem cmd parser treats `(...)` as block delimiters even inside quoted
rem strings, and an unescaped `)` in `print(sys.executable)` closes an
rem outer block, producing cryptic errors.

set "STAMPS=%~dp0.."
for %%A in ("%STAMPS%") do set "STAMPS=%%~fA"
set "PATH=%STAMPS%\bin;%STAMPS%\external\snaphu\bin;%STAMPS%\external\triangle\bin;%PATH%"
set "PYTHONPATH=%STAMPS%\python;%PYTHONPATH%"

rem Override resolution: respect PHASE's shared-config first if present.
set "STAMPS_PYTHON="
if exist "%APPDATA%\PHASE\python.txt" set /p STAMPS_PYTHON=<"%APPDATA%\PHASE\python.txt"

if defined STAMPS_PYTHON (
    "%STAMPS_PYTHON%" -m stamps.mt_prep_snap %*
    exit /b %ERRORLEVEL%
)

rem No PHASE config — try `py -3` (python.org launcher), then `python` on PATH.
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 -m stamps.mt_prep_snap %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python -m stamps.mt_prep_snap %*
    exit /b %ERRORLEVEL%
)

echo ERROR: No Python 3.11+ found. Install from https://www.python.org >&2
exit /b 9009
