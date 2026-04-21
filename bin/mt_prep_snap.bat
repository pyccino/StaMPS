@echo off
setlocal enabledelayedexpansion
rem StaMPS Windows shim: delegates to the Python port.
rem
rem setlocal enabledelayedexpansion is REQUIRED: %ERRORLEVEL% is expanded
rem at block-PARSE time, so `if (python -m ... & exit /b %ERRORLEVEL%)`
rem would always exit with the pre-call errorlevel. !ERRORLEVEL! expands
rem at runtime (delayed-expansion) so post-call errorlevel propagates.
rem
rem chcp 65001 forces UTF-8 on the console so non-ASCII argv (e.g. CJK
rem paths) survives the cmd.exe -> python.exe handoff; original CP is
rem restored at :_cleanup. Active CP is queried via PowerShell because
rem the `chcp` command's output text is localized on non-English Windows
rem (Italian: "Pagina codici attiva: 437") and would defeat a naive
rem `for /f "tokens=2 delims=:"` parse.

set "_ORIG_CP="
for /f %%c in ('powershell -NoProfile -Command "[console]::OutputEncoding.CodePage" 2^>nul') do set "_ORIG_CP=%%c"
chcp 65001 >nul 2>&1

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
set "_RC=9009"
goto :_cleanup

:check_stub
rem Detect Microsoft Store Python stub. The Store ships a fake `python.exe`
rem under %LOCALAPPDATA%\Microsoft\WindowsApps\ that opens the Store UI on
rem first invocation instead of running Python. `sys.executable` is an
rem absolute path that still contains `\WindowsApps\`, so we (a) verify
rem the interpreter can execute `import sys` and (b) reject any resolved
rem path under \WindowsApps\.
rem
rem Capture via temp file (NOT `for /f`): when PYTHON_EXE is a quoted .bat
rem path (e.g. STAMPS_PYTHON pointing at a venv wrapper), `for /f` spawns
rem `cmd /c ""C:\path\wrapper.bat" -c "..."` and the inner cmd's quote-strip
rem pass mangles the executable token, producing "command not recognized".
rem Plus: invoking a .bat without `call` lets its `exit /b` terminate this
rem script, so `call` is required here AND in the -m delegation below.
set "_TMPRES=%TEMP%\_stamps_resolved_%RANDOM%_%RANDOM%.txt"
call %PYTHON_EXE% -c "import sys; print(sys.executable)" > "%_TMPRES%" 2>nul
set "RESOLVED_PY="
if exist "%_TMPRES%" (
    set /p RESOLVED_PY=<"%_TMPRES%"
    del /q "%_TMPRES%" 2>nul
)
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

call %PYTHON_EXE% -m stamps.mt_prep_snap %*
set "_RC=!errorlevel!"
goto :_cleanup

:_cleanup
if defined _ORIG_CP chcp !_ORIG_CP! >nul 2>&1
exit /b !_RC!
