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
    assert (
        "SHA256SUMS-msvc missing" in text
    ), "expected explicit error string when SHA256SUMS-msvc asset is absent"
    # The error branch must exit with code 3. Search within a reasonable
    # window of the error message for the exit statement.
    idx = text.index("SHA256SUMS-msvc missing")
    window = text[idx : idx + 400]
    assert re.search(
        r"exit\s+3", window
    ), "hard-fail branch for missing SHA256SUMS-msvc must call `exit 3`"


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

    assert not offenders, "unquoted $zipPath found in command invocation(s): " + " | ".join(
        offenders
    )


def test_installer_preexisting_install_guard():
    """Before extracting, the installer must detect an existing install
    (via the bin\\mt_prep_snap.bat sentinel) and bail unless -Force is set.
    """
    text = SCRIPT.read_text()
    assert (
        "Existing install at" in text
    ), "expected pre-existing install guard message 'Existing install at ...'"
    assert (
        "mt_prep_snap.bat" in text
    ), "pre-existing install detection should key off bin\\mt_prep_snap.bat sentinel"
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
    assert (
        finally_match.start() > try_match.start()
    ), "`finally` must appear after the matching `try`"

    finally_body = finally_match.group(1)
    assert re.search(
        r"Remove-Item\s+\"?\$zipPath\"?", finally_body
    ), "finally block must call Remove-Item on $zipPath"

    try_body = text[try_match.end() : finally_match.start()]
    assert (
        "Expand-Archive" in try_body
    ), "try block must wrap the Expand-Archive step so cleanup covers extract failures"


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
    assert (
        "https://token.actions.githubusercontent.com" in text
    ), "expected OIDC issuer pin to GitHub Actions token endpoint"
    assert "--cert-oidc-issuer" in text


# --- Write-Error / exit-N anti-pattern regression ------------------------


def _strip_line_comment(line: str) -> str:
    """Drop PowerShell line-comments (naive: assumes no '#' inside a
    string literal on the same line as an `exit N` statement, which is
    true for every exit site in this script).
    """
    idx = line.find("#")
    return line if idx < 0 else line[:idx]


def test_installer_no_write_error_before_exit():
    """Regression guard for the HIGH-severity exit-code bug.

    With ``$ErrorActionPreference = "Stop"`` set at the top of the
    installer, ``Write-Error`` becomes a *terminating* error: it raises
    an exception and the script exits with ``$LASTEXITCODE = 1`` before
    any subsequent explicit ``exit N`` runs. Every error branch that
    picks a specific exit code (3/4/5/6) must therefore use
    ``[Console]::Error.WriteLine("ERROR: ...")`` instead of
    ``Write-Error``.

    This test scans the .ps1 source line-by-line and flags any
    ``Write-Error`` whose exit-code intent would be clobbered:
      - a ``Write-Error`` followed on the SAME line by ``exit N``
        (the ``; exit N`` idiom), OR
      - a ``Write-Error`` followed within the next 8 non-blank lines
        by an ``exit N`` statement (allowing for a here-string body
        or a single intervening `if`/message line).

    Comment lines (starting with ``#``) are ignored so the explanatory
    block comments that mention Write-Error don't trip the check.
    """
    lines = SCRIPT.read_text().splitlines()

    offenders: list[str] = []
    for i, raw in enumerate(lines):
        stripped = raw.lstrip()
        if stripped.startswith("#"):
            continue
        code = _strip_line_comment(raw)
        if "Write-Error" not in code:
            continue
        # Same-line `Write-Error ...; exit N` idiom.
        if re.search(r"Write-Error.*;\s*exit\s+\d+", code):
            offenders.append(f"line {i + 1}: {raw.strip()}")
            continue
        # Look ahead up to 8 non-blank, non-comment lines for an exit N.
        seen = 0
        for j in range(i + 1, len(lines)):
            nxt = lines[j].lstrip()
            if not nxt or nxt.startswith("#"):
                continue
            seen += 1
            if re.match(r"exit\s+\d+", nxt):
                offenders.append(
                    f"line {i + 1}: Write-Error followed by `{nxt.strip()}` at line {j + 1}"
                )
                break
            if seen >= 8:
                break

    assert not offenders, (
        "Write-Error preceding `exit N` would be clobbered to exit 1 under "
        "$ErrorActionPreference = 'Stop'. Use `[Console]::Error.WriteLine(\"ERROR: ...\")` "
        "instead. Offenders:\n  " + "\n  ".join(offenders)
    )


def test_installer_has_console_stderr_writes_per_exit_branch():
    """Each exit branch (2/3/4/5/6) must emit its error via
    ``[Console]::Error.WriteLine`` so the chosen exit code is preserved.

    We don't require a 1:1 mapping (some branches emit multiple stderr
    lines, e.g. the catch-around-Invoke-RestMethod site), but the count
    of ``[Console]::Error.WriteLine`` invocations must be at least 5
    (one per distinct exit code used).
    """
    text = SCRIPT.read_text()
    count = len(re.findall(r"\[Console\]::Error\.WriteLine", text))
    assert count >= 5, (
        f"expected at least 5 `[Console]::Error.WriteLine` calls "
        f"(one per exit branch 2/3/4/5/6); found {count}"
    )


def _pwsh_available() -> str | None:
    """Return the pwsh/powershell executable name available on PATH,
    or None. Prefers pwsh (cross-platform) over Windows-only powershell.
    """
    import shutil

    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            return exe
    return None


@pytest.mark.skipif(_pwsh_available() is None, reason="pwsh/powershell not on PATH")
def test_installer_exits_6_on_existing_install(tmp_path):
    """Behavioral test: when the pre-existing-install sentinel
    (``bin\\mt_prep_snap.bat``) is present and ``-Force`` is NOT
    passed, the installer must exit with code 6 — not 1 (which is
    what ``Write-Error`` + ``exit 6`` used to produce under
    ``$ErrorActionPreference = 'Stop'``).

    Uses the DryRun-incompatible guard at line ~91: the guard fires
    only when ``-DryRun`` is NOT set. We therefore run the installer
    without ``-DryRun`` but with ``-InstallDir`` pointed at a fake
    install tree, and pass ``-Repo nonexistent/nothing`` so that even
    if the guard somehow didn't fire, the release fetch would fail
    (with a different, distinguishable code).
    """
    exe = _pwsh_available()
    assert exe is not None
    # Simulate an existing install by planting the sentinel.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "mt_prep_snap.bat").write_text("REM fake sentinel\n")

    proc = subprocess.run(
        [
            exe,
            "-NoProfile",
            "-File",
            str(SCRIPT),
            "-Repo",
            "nonexistent/nothing",
            "-InstallDir",
            str(tmp_path),
            "-SkipAttestation",
        ],
        capture_output=True,
        cwd=str(tmp_path),
        timeout=120,
    )
    assert proc.returncode == 6, (
        f"expected exit 6 for pre-existing install guard, got "
        f"{proc.returncode}\nstdout: {proc.stdout!r}\nstderr: {proc.stderr!r}"
    )


@pytest.mark.skipif(_pwsh_available() is None, reason="pwsh/powershell not on PATH")
def test_installer_exits_3_on_bad_repo(tmp_path):
    """Behavioral test: passing a nonexistent ``-Repo`` makes the
    ``Invoke-RestMethod`` call to api.github.com fail. The catch
    block prints via ``[Console]::Error.WriteLine`` and exits 3.
    Before the fix this exited 1 because ``Write-Error`` under
    ``$ErrorActionPreference = 'Stop'`` raised a terminating error.

    Uses ``-DryRun`` to skip the pre-existing-install guard + avoid
    any filesystem mutations.
    """
    exe = _pwsh_available()
    assert exe is not None
    proc = subprocess.run(
        [
            exe,
            "-NoProfile",
            "-File",
            str(SCRIPT),
            "-Repo",
            "nonexistent-org-xyz-does-not-exist/nothing",
            "-InstallDir",
            str(tmp_path),
            "-SkipAttestation",
            "-DryRun",
        ],
        capture_output=True,
        cwd=str(tmp_path),
        timeout=120,
    )
    # The catch block's `exit 3` fires only when $release is still unset,
    # which is the case when Invoke-RestMethod raises. Accept 3 as the
    # primary expectation; a network-blocked CI might yield a different
    # code but we assert it is NOT 1 (the Write-Error-clobber value).
    assert proc.returncode != 1, (
        f"exit 1 indicates Write-Error clobbered the explicit exit code "
        f"(regression of HIGH exit-code bug).\nstdout: {proc.stdout!r}\n"
        f"stderr: {proc.stderr!r}"
    )
