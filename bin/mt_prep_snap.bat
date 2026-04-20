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

rem Select which interpreter invocation to use. PYTHON_EXE is whatever
rem token(s) cmd.exe should exec: a quoted absolute path, `py -3`, or
rem `python`. The Microsoft-Store-stub guard below runs once, at file
rem scope, regardless of which branch was taken.
set "PYTHON_EXE="
if defined STAMPS_PYTHON (
    set PYTHON_EXE="!STAMPS_PYTHON!"
    goto :check_stub
)

rem Try `py -3` (python.org launcher) first.
where py >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py -3"
    goto :check_stub
)

rem Fall back to plain `python` on PATH.
where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=python"
    goto :check_stub
)

echo ERROR: No Python 3.11+ found. Install from https://www.python.org >&2
exit /b 9009

:check_stub
rem Detect Microsoft Store Python stub. The Store ships a fake `python.exe`
rem under %LOCALAPPDATA%\Microsoft\WindowsApps\ that opens the Store UI on
rem first invocation instead of running Python. `sys.executable` is an
rem absolute path that still contains `\WindowsApps\`, so we (a) verify
rem the interpreter can execute `import sys` and (b) reject any resolved
rem path under \WindowsApps\.
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

%PYTHON_EXE% -m stamps.mt_prep_snap %*
exit /b !errorlevel!
