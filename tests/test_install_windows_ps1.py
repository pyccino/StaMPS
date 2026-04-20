"""Tests for install-windows.ps1.

These tests are Windows-only: the installer is a PowerShell script that
probes Windows-specific behaviors (registry, WSL detection, TLS 1.2
default). On Linux/macOS the ``windows_only`` marker causes them to be
skipped at collection time.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "install-windows.ps1"


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="Windows installer only")
def test_installer_dry_run_aborts_in_wsl(tmp_path, monkeypatch):
    """Abort if WSL_DISTRO_NAME is set."""
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-File", str(SCRIPT), "-DryRun"],
        capture_output=True, cwd=tmp_path
    )
    assert proc.returncode == 2


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="Windows installer only")
def test_installer_forces_tls12():
    """Grep the script text for the TLS 1.2 line."""
    text = SCRIPT.read_text()
    assert "SecurityProtocolType]::Tls12" in text


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="Windows installer only")
def test_installer_verifies_attestation():
    text = SCRIPT.read_text()
    assert "gh attestation verify" in text
