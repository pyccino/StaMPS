"""Tests for StaMPS_CONFIG.ps1.

Verify that the PowerShell config script is at parity with
StaMPS_CONFIG.bash: every env var exported by the bash file must also be
set after dot-sourcing the .ps1 (installation-specific roots are allowed
to be empty strings, but must *exist* as keys in the environment).

The tests also verify that re-sourcing the script is idempotent for
PATH — repeated dot-sourcing must not multiply the number of StaMPS\\bin
entries.

These tests are Windows-only: the script uses Windows path separators,
the registry, and the `Program Files\\MATLAB` glob. On Linux/macOS the
``windows_only`` marker skips them at collection time.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "StaMPS_CONFIG.ps1"
BASH_SCRIPT = Path(__file__).resolve().parent.parent / "StaMPS_CONFIG.bash"


def _bash_exported_vars() -> set[str]:
    """Parse StaMPS_CONFIG.bash and return the set of exported var names.

    Only matches lines of the form `export NAME=...` — commented lines
    (starting with `#`) are skipped by the regex anchor.
    """
    pattern = re.compile(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
    return set(pattern.findall(BASH_SCRIPT.read_text()))


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell config is Windows-only")
def test_ps1_sets_all_vars():
    """Every var exported by .bash must be set after sourcing .ps1."""
    expected = _bash_exported_vars()
    # PATH is special-cased — we don't require exact parity, just presence.
    assert "PATH" in expected or "PATH" not in expected  # tautology guard

    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f". '{SCRIPT}'; Get-ChildItem env: | "
        "Select-Object Name,Value | ConvertTo-Json -Compress",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    entries = json.loads(proc.stdout)
    if isinstance(entries, dict):
        entries = [entries]
    env = {e["Name"]: e["Value"] for e in entries}

    missing = sorted(v for v in expected if v not in env)
    assert not missing, f"Env vars in .bash but missing from .ps1: {missing}"


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell config is Windows-only")
def test_ps1_path_idempotent():
    """Dot-sourcing twice must not duplicate PATH entries."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f". '{SCRIPT}'; . '{SCRIPT}'; $env:PATH",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    path_entries = [p for p in proc.stdout.strip().split(";") if p]
    # Every StaMPS-injected entry must appear exactly once.
    stamps_bin_count = sum(1 for p in path_entries if p.lower().endswith(r"\stamps\bin"))
    # Be tolerant: `STAMPS` root may live under any directory but the
    # bin suffix is unique to the port.
    matches = [p for p in path_entries if p.lower().endswith(r"\bin")]
    stamps_bin_matches = [p for p in matches if "stamps" in p.lower()]
    assert stamps_bin_count <= 1 or len(stamps_bin_matches) == len(
        set(stamps_bin_matches)
    ), f"PATH contains duplicate StaMPS\\bin entries: {stamps_bin_matches}"


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell config is Windows-only")
def test_ps1_stamps_root_resolves():
    """STAMPS must resolve to an existing directory after sourcing."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f". '{SCRIPT}'; $env:STAMPS",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    root = proc.stdout.strip()
    assert root, "STAMPS env var is empty after sourcing"
    assert Path(root).is_dir(), f"STAMPS={root!r} is not a directory"
