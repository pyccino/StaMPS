# Dot-source to configure the StaMPS environment in PowerShell:
#   . C:\path\to\StaMPS\StaMPS_CONFIG.ps1
# For programmatic invocation (PHASE, CI), use bin\mt_prep_snap.bat which
# self-bootstraps the environment from %~dp0.
#
# This file mirrors StaMPS_CONFIG.bash / .tcsh variable-for-variable so
# that downstream scripts (make_raw_*.pl, roi_prep.pl, doris runners) can
# rely on the same environment regardless of host shell.
#
# Installation-specific roots (SAR, GETORB_BIN, DORIS_BIN, etc.) default
# to empty strings — PowerShell has no distinct "unset" vs "empty" state,
# so "" matches the behavior of an unquoted-empty bash variable for the
# downstream consumers that check `if [ -n "$FOO" ]`. Set these to real
# paths by editing this file or exporting them before dot-sourcing.

$env:STAMPS = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Installation-specific roots (blank by default; edit as needed) ---
$env:SAR          = ""
$env:GETORB_BIN   = ""
$env:SAR_ODR_DIR  = ""
$env:VOR_DIR      = ""
$env:INS_DIR      = ""
$env:DORIS_BIN    = ""
$env:SAR_TAPE     = ""

# --- Bundled external tools (ship with the Windows port) ---
$env:SNAPHU_BIN   = "$env:STAMPS\external\snaphu\bin"
$env:TRIANGLE_BIN = "$env:STAMPS\external\triangle\bin"

# --- ROI_PAC v3 layout (derived from $SAR) ---
$env:ROI_PAC  = "$env:SAR\ROI_PAC"
$env:INT_BIN  = "$env:ROI_PAC\INT_BIN"
$env:INT_SCR  = "$env:ROI_PAC\INT_SCR"

# --- "Shouldn't need to change below here" block from .bash ---
$env:MY_BIN    = "$env:INT_BIN"
$env:DORIS_SCR = "$env:STAMPS\DORIS_SCR"
$env:MY_SAR    = "$env:SAR"
$env:OUR_SCR   = "$env:MY_SAR\OUR_SCR"
$env:MY_SCR    = "$env:STAMPS\ROI_PAC_SCR"

# MATLABPATH — matlab_compat MUST come BEFORE matlab so shims override
$env:MATLABPATH = "$env:STAMPS\matlab_compat;$env:STAMPS\matlab;$env:MATLABPATH"
$env:PYTHONPATH = "$env:STAMPS\python;$env:PYTHONPATH"

# Locale (advisory on Windows; see INSTALL.md)
$env:LC_NUMERIC = "en_US.UTF-8"
$env:LC_TIME    = "en_US.UTF-8"

# --- PATH additions with idempotency guard ---
# Re-dot-sourcing must not append duplicates. Each entry is checked
# individually so that partial overlaps (e.g. user already prepended
# STAMPS\bin but not SNAPHU_BIN) don't skip the remaining entries.
#
# Comparison is done per-segment on `;`-split PATH with case-insensitive
# exact match (Windows PATH is case-insensitive). A naive substring
# test would false-positive when e.g. STAMPS\bin is C:\stamps\bin and
# PATH already contains C:\stamps\bin\extras.
$pathAdditions = @(
    "$env:STAMPS\bin",
    "$env:SNAPHU_BIN",
    "$env:TRIANGLE_BIN",
    "$env:MY_SCR",
    "$env:INT_BIN",
    "$env:INT_SCR",
    "$env:OUR_SCR",
    "$env:DORIS_SCR",
    "$env:GETORB_BIN",
    "$env:DORIS_BIN"
)
foreach ($toAdd in $pathAdditions) {
    if ([string]::IsNullOrEmpty($toAdd)) { continue }
    $segments = $env:PATH -split ';' | Where-Object { $_ }
    if ($segments -inotcontains $toAdd) {
        $env:PATH = "$toAdd;$env:PATH"
    }
}

# --- MATLAB_EXE autodetection with layered fallbacks ---
# 1. Honour pre-set $env:MATLAB_EXE if the file exists.
# 2. Glob C:\Program Files\MATLAB\R*\bin\matlab.exe (newest first).
# 3. Consult the registry: HKLM\SOFTWARE\Mathworks\MATLAB\<ver>\MATLABROOT.
# 4. Fall back to PATH lookup via Get-Command.
# 5. Warn and leave unset if nothing works.
if ($env:MATLAB_EXE -and (Test-Path $env:MATLAB_EXE)) {
    # Honour caller's explicit choice.
} else {
    $env:MATLAB_EXE = $null

    # Step 2: Program Files glob
    $found = Get-ChildItem -Path "C:\Program Files\MATLAB\R*\bin\matlab.exe" `
        -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { $env:MATLAB_EXE = $found.FullName }

    # Step 3: registry
    if (-not $env:MATLAB_EXE) {
        # Windows registry paths are case-insensitive, so "Mathworks"
        # matches both "MathWorks" and "MATHWORKS" installations — no
        # need to enumerate case variants here.
        $regHit = Get-ItemProperty -Path "HKLM:\SOFTWARE\Mathworks\MATLAB\*" -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($_.MATLABROOT) { Join-Path $_.MATLABROOT 'bin\matlab.exe' }
            } |
            Where-Object { $_ -and (Test-Path $_) } |
            Sort-Object -Descending | Select-Object -First 1
        if ($regHit) { $env:MATLAB_EXE = $regHit }
    }

    # Step 4: PATH search
    if (-not $env:MATLAB_EXE) {
        $cmd = Get-Command matlab.exe -ErrorAction SilentlyContinue
        if ($cmd) { $env:MATLAB_EXE = $cmd.Source }
    }

    # Step 5: give up with a warning
    if (-not $env:MATLAB_EXE) {
        Write-Warning "MATLAB_EXE could not be auto-detected. Set `$env:MATLAB_EXE manually before running MATLAB-dependent steps."
    }
}

Write-Host "StaMPS environment configured:"
Write-Host "  STAMPS   = $env:STAMPS"
Write-Host "  MATLAB   = $env:MATLAB_EXE"
