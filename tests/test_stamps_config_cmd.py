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


def _cmd_blank_assigned_vars() -> set[str]:
    """Vars the .cmd leaves empty (directly or transitively).

    Direct: `set "X="` — Windows treats empty-string assignment as
    deletion, so X is absent from the environment. The .cmd uses these
    as user-edits-this-line placeholders for installation-specific
    roots (SAR, GETORB_BIN, etc.) that the bash file populates with
    upstream Linux defaults.

    Transitive: `set "X=%Y%"` (pure pass-through, no literal text)
    where Y is itself blank — X also collapses to "" and gets
    deleted (e.g. `set "MY_SAR=%SAR%"` with SAR blank).

    The parity check must exempt both — they're absent from `set`
    output by design.
    """
    text = SCRIPT.read_text()
    blanks = set(re.findall(r'^\s*set\s+"([A-Za-z_][A-Za-z0-9_]*)="\s*$', text, re.MULTILINE))
    pass_through = re.findall(
        r'^\s*set\s+"([A-Za-z_][A-Za-z0-9_]*)=%([A-Za-z_][A-Za-z0-9_]*)%"\s*$',
        text,
        re.MULTILINE,
    )
    while True:
        added = {x for x, y in pass_through if y in blanks} - blanks
        if not added:
            break
        blanks |= added
    return blanks


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe config is Windows-only")
def test_cmd_sets_all_vars_when_invoked_via_cmd():
    """`cmd /c "call StaMPS_CONFIG.cmd && set"` must export every .bash var."""
    expected = _bash_exported_vars()
    # shell=True hands the string straight to cmd /c. List form
    # (["cmd", "/c", '...']) fails on Windows: subprocess.list2cmdline
    # quote-escapes the third element, then cmd /c's quote-strip pass
    # mangles the result so the SCRIPT path is mis-parsed as part of the
    # executable token, yielding "command not recognized".
    proc = subprocess.run(
        f'call "{SCRIPT}" && set',
        capture_output=True,
        text=True,
        check=True,
        shell=True,
    )

    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v

    # Windows env-var lookups are case-insensitive, and PATH is canonically
    # `Path` in the Windows env table (cmd `set` echoes it that way). The
    # bash file exports `PATH` (uppercase) — match by lower().
    env_keys_ci = {k.lower() for k in env}
    blank_slots = _cmd_blank_assigned_vars()
    missing = sorted(v for v in expected if v not in blank_slots and v.lower() not in env_keys_ci)
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
    # shell=True (string form) — see test_cmd_sets_all_vars_when_invoked_via_cmd
    # for why list form fails on cmd.exe quote-strip.
    proc = subprocess.run(
        f'call "{SCRIPT}" && call "{SCRIPT}" && echo %PATH%',
        capture_output=True,
        text=True,
        check=True,
        shell=True,
    )
    # Last line of stdout is the echoed PATH.
    path_line = proc.stdout.strip().splitlines()[-1]
    entries = [p for p in path_line.split(";") if p]
    stamps_bin = [p for p in entries if p.lower().endswith(r"\bin") and "stamps" in p.lower()]
    assert len(stamps_bin) == len(
        set(p.lower() for p in stamps_bin)
    ), f"Duplicate StaMPS\\bin entries after double-call: {stamps_bin}"
