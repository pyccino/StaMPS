@echo off
rem Configure the StaMPS environment in a cmd.exe session.
rem
rem Usage (from cmd.exe):
rem     call StaMPS_CONFIG.cmd
rem
rem A plain `StaMPS_CONFIG.cmd` without `call` still works for the current
rem script but env vars die with the child process. `call` is required
rem when sourcing from another batch file so the variables propagate to
rem the caller.
rem
rem This mirrors StaMPS_CONFIG.bash variable-for-variable.

rem ---- Guard: must be running under cmd.exe ---------------------------
rem CMDEXTVERSION is only defined inside cmd.exe (with command extensions
rem enabled, which is the default since Windows 2000). Powershell, pwsh
rem and other hosts do not set it.
if not defined CMDEXTVERSION (
    echo This script must be invoked from cmd.exe via ^`call StaMPS_CONFIG.cmd^`.
    echo For PowerShell use:  . .\StaMPS_CONFIG.ps1
    exit /b 1
)

rem ---- STAMPS root = directory containing this script ---------------
rem %~dp0 expands to the drive+path of this .cmd, with a trailing
rem backslash; strip it for consistency with the bash export.
set "STAMPS=%~dp0"
if "%STAMPS:~-1%"=="\" set "STAMPS=%STAMPS:~0,-1%"

rem ---- Installation-specific roots (blank by default) --------------
set "SAR="
set "GETORB_BIN="
set "SAR_ODR_DIR="
set "VOR_DIR="
set "INS_DIR="
set "DORIS_BIN="
set "SAR_TAPE="

rem ---- Bundled external tools --------------------------------------
set "SNAPHU_BIN=%STAMPS%\external\snaphu\bin"
set "TRIANGLE_BIN=%STAMPS%\external\triangle\bin"

rem ---- ROI_PAC v3 layout (derived) ---------------------------------
set "ROI_PAC=%SAR%\ROI_PAC"
set "INT_BIN=%ROI_PAC%\INT_BIN"
set "INT_SCR=%ROI_PAC%\INT_SCR"

rem ---- "Shouldn't need to change below here" -----------------------
set "MY_BIN=%INT_BIN%"
set "DORIS_SCR=%STAMPS%\DORIS_SCR"
set "MY_SAR=%SAR%"
set "OUR_SCR=%MY_SAR%\OUR_SCR"
set "MY_SCR=%STAMPS%\ROI_PAC_SCR"

rem MATLABPATH - matlab_compat MUST come BEFORE matlab so shims override
set "MATLABPATH=%STAMPS%\matlab_compat;%STAMPS%\matlab;%MATLABPATH%"
set "PYTHONPATH=%STAMPS%\python;%PYTHONPATH%"

rem ---- Locale (advisory on Windows; see INSTALL.md) ---------------
set "LC_NUMERIC=en_US.UTF-8"
set "LC_TIME=en_US.UTF-8"

rem ---- PATH additions with per-entry duplicate guard --------------
rem findstr /i /c:"..." is case-insensitive substring match on %PATH%.
rem Each entry is guarded separately so partial overlaps don't skip
rem the remaining additions.
call :_add_path "%STAMPS%\bin"
call :_add_path "%SNAPHU_BIN%"
call :_add_path "%TRIANGLE_BIN%"
call :_add_path "%MY_SCR%"
call :_add_path "%INT_BIN%"
call :_add_path "%INT_SCR%"
call :_add_path "%OUR_SCR%"
call :_add_path "%DORIS_SCR%"
call :_add_path "%GETORB_BIN%"
call :_add_path "%DORIS_BIN%"

echo StaMPS environment configured:
echo   STAMPS   = %STAMPS%
goto :eof

rem ---- Subroutine: prepend %~1 to PATH if not already there -------
:_add_path
if "%~1"=="" goto :eof
echo %PATH% | findstr /i /c:"%~1" >nul
if errorlevel 1 set "PATH=%~1;%PATH%"
goto :eof
