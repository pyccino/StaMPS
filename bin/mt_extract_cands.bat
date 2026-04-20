@echo off
setlocal enabledelayedexpansion
rem StaMPS Windows shim: delegates to the Python port.
rem See mt_prep_snap.bat for design notes.
rem
rem chcp 65001 forces UTF-8 so non-ASCII argv survives cmd.exe; original
rem CP is restored at :_cleanup. PowerShell is used to query the active
rem CP because `chcp`'s output text is localized on non-English Windows.

set "_ORIG_CP="
for /f %%c in ('powershell -NoProfile -Command "[console]::OutputEncoding.CodePage" 2^>nul') do set "_ORIG_CP=%%c"
chcp 65001 >nul 2>&1

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
set "_RC=9009"
goto :_cleanup

:check_stub
for /f "tokens=*" %%i in ('%PYTHON_EXE% -c "import sys; print(sys.executable)" 2^>nul') do set RESOLVED_PY=%%i
if "!RESOLVED_PY!"=="" (
    echo ERROR: Python launcher at "!PYTHON_EXE!" failed to run "import sys". >&2
    echo This is typically the Microsoft Store stub. Install real Python 3.11+ from https://www.python.org. >&2
    set "_RC=9"
    goto :_cleanup
)
echo !RESOLVED_PY! | findstr /I "\\WindowsApps\\" >nul
if !errorlevel! equ 0 (
    echo ERROR: "!RESOLVED_PY!" is the Microsoft Store Python stub. >&2
    echo Install real Python 3.11+ from https://www.python.org and ensure it's ahead on PATH. >&2
    set "_RC=9"
    goto :_cleanup
)

%PYTHON_EXE% -m stamps.mt_extract_cands %*
set "_RC=!errorlevel!"
goto :_cleanup

:_cleanup
if defined _ORIG_CP chcp !_ORIG_CP! >nul 2>&1
exit /b !_RC!
