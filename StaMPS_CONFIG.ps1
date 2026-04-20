# Dot-source to configure the StaMPS environment in PowerShell:
#   . C:\path\to\StaMPS\StaMPS_CONFIG.ps1
# For programmatic invocation (PHASE, CI), use bin\mt_prep_snap.bat which
# self-bootstraps the environment from %~dp0.

$env:STAMPS = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:SNAPHU_BIN = "$env:STAMPS\external\snaphu\bin"
$env:TRIANGLE_BIN = "$env:STAMPS\external\triangle\bin"

# MATLABPATH — matlab_compat MUST come BEFORE matlab so shims override
$env:MATLABPATH = "$env:STAMPS\matlab_compat;$env:STAMPS\matlab;$env:MATLABPATH"
$env:PYTHONPATH = "$env:STAMPS\python;$env:PYTHONPATH"
$env:PATH = "$env:STAMPS\bin;$env:SNAPHU_BIN;$env:TRIANGLE_BIN;$env:PATH"

# Locale (advisory on Windows; see INSTALL.md)
$env:LC_NUMERIC = "en_US.UTF-8"
$env:LC_TIME = "en_US.UTF-8"

# MATLAB_EXE autodetection — pick newest Rxxx
if (-not $env:MATLAB_EXE) {
    $found = Get-ChildItem -Path "C:\Program Files\MATLAB\R*\bin\matlab.exe" `
        -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { $env:MATLAB_EXE = $found.FullName }
}

Write-Host "StaMPS environment configured:"
Write-Host "  STAMPS   = $env:STAMPS"
Write-Host "  MATLAB   = $env:MATLAB_EXE"
