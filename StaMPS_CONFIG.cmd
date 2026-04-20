@echo off
rem Thin cmd.exe wrapper that shells to PowerShell for real env setup.
rem Note: env vars set in the PS child process die with it; this wrapper
rem is informational only. Use mt_prep_snap.bat for invocations.
powershell -NoProfile -ExecutionPolicy Bypass -Command ". '%~dp0StaMPS_CONFIG.ps1'; Write-Host 'Environment configured in that PowerShell only.'"
