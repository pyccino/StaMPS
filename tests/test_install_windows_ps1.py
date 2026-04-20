"""Tests for install-windows.ps1.

The invocation-based tests are Windows-only: they actually run the
PowerShell script and probe Windows-specific behaviours (registry, WSL
detection, TLS 1.2 default). On Linux/macOS the ``windows_only`` marker
causes them to be skipped at collection time.

The static-grep tests below are unmarked: they read the .ps1 source as
text and verify hardening invariants (hard-fail on missing SHA256 asset,
quoted path vars, temp cleanup on failure, pre-existing install guard).
These run on any host and catch regressions in CI without needing a
PowerShell runtime.
"""

from __future__ import annotations

import re
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
        capture_output=True,
        cwd=tmp_path,
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


# --- Static-grep hardening tests (run on any host) -----------------------


def test_installer_rejects_missing_sha256sums():
    """SHA256 verification is mandatory: missing SHA256SUMS-msvc must
    produce a hard error with exit code 3, not a silent skip.
    """
    text = SCRIPT.read_text()
    assert "SHA256SUMS-msvc missing" in text, (
        "expected explicit error string when SHA256SUMS-msvc asset is absent"
    )
    # The error branch must exit with code 3. Search within a reasonable
    # window of the error message for the exit statement.
    idx = text.index("SHA256SUMS-msvc missing")
    window = text[idx : idx + 400]
    assert re.search(r"exit\s+3", window), (
        "hard-fail branch for missing SHA256SUMS-msvc must call `exit 3`"
    )


def test_installer_quotes_path_vars():
    """$zipPath must be double-quoted in all external-command and
    file-manipulation invocations so install paths containing spaces
    (e.g. C:\\Program Files\\StaMPS) don't splat into extra tokens.

    The check is deliberately narrow: we forbid the bare token
    `$zipPath` appearing unquoted as an argument to `gh`, `Expand-Archive`,
    `Remove-Item`, or `Get-FileHash`. The token is only acceptable when
    wrapped in double quotes: `"$zipPath"`.
    """
    text = SCRIPT.read_text()

    # Commands that take $zipPath as an argument and therefore require
    # the variable to be quoted.
    commands = [
        r"gh\s+attestation\s+verify",
        r"Expand-Archive",
        r"Remove-Item",
        r"Get-FileHash(?:\s+-Algorithm\s+\S+)?",
        r"Invoke-WebRequest",
        r"Test-Path",
    ]

    offenders: list[str] = []
    for line in text.splitlines():
        # Skip comment-only lines — they're documentation, not executed.
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for cmd in commands:
            # Match only lines that actually invoke the command AND
            # contain an unquoted $zipPath reference on the same line.
            if re.search(cmd, line) and re.search(r"(?<!\")\$zipPath(?!\")", line):
                offenders.append(line.strip())
                break

    assert not offenders, (
        "unquoted $zipPath found in command invocation(s): " + " | ".join(offenders)
    )


def test_installer_preexisting_install_guard():
    """Before extracting, the installer must detect an existing install
    (via the bin\\mt_prep_snap.bat sentinel) and bail unless -Force is set.
    """
    text = SCRIPT.read_text()
    assert "Existing install at" in text, (
        "expected pre-existing install guard message 'Existing install at ...'"
    )
    assert "mt_prep_snap.bat" in text, (
        "pre-existing install detection should key off bin\\mt_prep_snap.bat sentinel"
    )
    assert "-Force" in text, "pre-existing install guard must advertise -Force escape hatch"


def test_installer_cleans_temp_on_failure():
    """Download + verify + extract must run inside a try/finally so the
    staging zip in %TEMP% is removed even when a step throws.

    Rather than try to match balanced braces with a regex, we assert:
      1. A `try {` block exists earlier in the file than a `} finally {`
         block.
      2. The finally block contains `Remove-Item` against $zipPath.
      3. The try block body contains `Expand-Archive` (so cleanup wraps
         the whole download+verify+extract flow, not just a sub-step).
    """
    text = SCRIPT.read_text()

    try_match = re.search(r"\btry\s*\{", text)
    assert try_match, "no `try {` block found"

    finally_match = re.search(r"\}\s*finally\s*\{([^}]*)\}", text, re.DOTALL)
    assert finally_match, "no `} finally { ... }` block found"
    assert finally_match.start() > try_match.start(), (
        "`finally` must appear after the matching `try`"
    )

    finally_body = finally_match.group(1)
    assert re.search(r"Remove-Item\s+\"?\$zipPath\"?", finally_body), (
        "finally block must call Remove-Item on $zipPath"
    )

    try_body = text[try_match.end() : finally_match.start()]
    assert "Expand-Archive" in try_body, (
        "try block must wrap the Expand-Archive step so cleanup covers extract failures"
    )


def test_installer_accepts_iacceptunverifiedrisk_switch():
    """The existing -SkipAttestation + new -IAcceptUnverifiedRisk opt-out
    pair must be declared as script parameters, not as magic strings.
    """
    text = SCRIPT.read_text()
    assert re.search(r"\[switch\]\$IAcceptUnverifiedRisk", text)
    assert re.search(r"\[switch\]\$SkipAttestation", text)
    assert re.search(r"\[switch\]\$EnableLongPaths", text)
    assert re.search(r"\[switch\]\$Force", text)


def test_installer_oidc_issuer_pin_or_warning():
    """Attestation verification should pin the OIDC issuer (gh 2.50+) or
    emit a visible warning that the trust root is unpinned.
    """
    text = SCRIPT.read_text()
    assert "https://token.actions.githubusercontent.com" in text, (
        "expected OIDC issuer pin to GitHub Actions token endpoint"
    )
    assert "--cert-oidc-issuer" in text
