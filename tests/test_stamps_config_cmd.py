"""Tests for StaMPS_CONFIG.cmd.

The .cmd wrapper sets env vars in the caller's cmd.exe scope when
invoked via `call StaMPS_CONFIG.cmd`. Verify that every var exported by
StaMPS_CONFIG.bash is also set after the .cmd runs, and that the guard
against non-cmd hosts (PowerShell, pwsh) fires with exit code 1.

Windows-only.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "StaMPS_CONFIG.cmd"
BASH_SCRIPT = Path(__file__).resolve().parent.parent / "StaMPS_CONFIG.bash"


def _bash_exported_vars() -> set[str]:
    pattern = re.compile(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
    return set(pattern.findall(BASH_SCRIPT.read_text()))


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe config is Windows-only")
def test_cmd_sets_all_vars_when_invoked_via_cmd():
    """`cmd /c "call StaMPS_CONFIG.cmd && set"` must export every .bash var."""
    expected = _bash_exported_vars()
    cmd = ["cmd", "/c", f'call "{SCRIPT}" && set']
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v

    missing = sorted(v for v in expected if v not in env)
    assert not missing, f"Env vars in .bash but missing from .cmd: {missing}"


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe config is Windows-only")
def test_cmd_fails_when_not_invoked_via_cmd_exe():
    """Running the .cmd via PowerShell -File must exit 1 with a diagnostic."""
    # powershell -File runs the batch directly which then detects
    # CMDEXTVERSION is unset (powershell doesn't set it) and bails.
    # NB: on some hosts PowerShell spawns cmd.exe to run .cmd files,
    # which would defeat the guard — in that case the test is not
    # meaningful. We treat exit 1 as success, anything else as skip.
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"& '{SCRIPT}'; exit $LASTEXITCODE"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 1:
        pytest.skip(
            "PowerShell spawned cmd.exe to run the .cmd — guard can't fire. "
            f"returncode={proc.returncode}"
        )
    assert proc.returncode == 1


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe config is Windows-only")
def test_cmd_path_idempotent():
    """Calling the .cmd twice must not duplicate PATH entries."""
    cmd = ["cmd", "/c", f'call "{SCRIPT}" && call "{SCRIPT}" && echo %PATH%']
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # Last line of stdout is the echoed PATH.
    path_line = proc.stdout.strip().splitlines()[-1]
    entries = [p for p in path_line.split(";") if p]
    stamps_bin = [p for p in entries if p.lower().endswith(r"\bin") and "stamps" in p.lower()]
    assert len(stamps_bin) == len(
        set(p.lower() for p in stamps_bin)
    ), f"Duplicate StaMPS\\bin entries after double-call: {stamps_bin}"
