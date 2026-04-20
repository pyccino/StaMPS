"""Cross-platform MATLAB batch invocation for the StaMPS Python port."""

from __future__ import annotations

import glob
import locale
import os
import shutil
import subprocess
import sys
from pathlib import Path

# CI opt-out flag, sampled at import time. Set ``STAMPS_SKIP_MATLAB=1`` in the
# environment to make :func:`run_batch` raise immediately instead of invoking
# MATLAB. Used by canary / smoke jobs on runners without a MATLAB license.
_SKIP_MATLAB: bool = os.environ.get("STAMPS_SKIP_MATLAB") == "1"


class MatlabNotFoundError(RuntimeError):
    """Raised when the matlab executable cannot be located."""


def escape_matlab_string(s: str) -> str:
    """Escape a string for use inside MATLAB single-quoted literal."""
    return s.replace("'", "''")


def _script_arg_for_run(script: Path, platform: str) -> str:
    """Return the string to pass inside MATLAB run('...')."""
    s = str(script)
    if platform == "win32":
        # MATLAB accepts forward slashes in run() on Windows, EXCEPT for UNC
        # paths, which must stay as \\server\share\...
        if not s.startswith("\\\\"):
            s = s.replace("\\", "/")
    return escape_matlab_string(s)


def build_cmd(
    script: Path,
    log: Path,
    platform: str | None = None,
    matlab_exe: Path | str | None = None,
    fallback_r: bool = False,
) -> tuple[list[str], str]:
    """Return (argv_list, mode).

    mode is one of: 'stdin' (Linux), 'batch' (Windows R2019a+), 'r' (fallback).
    """
    plat = platform or sys.platform
    exe = str(matlab_exe) if matlab_exe else ("matlab.exe" if plat == "win32" else "matlab")

    if plat == "win32":
        run_arg = _script_arg_for_run(script, plat)
        if fallback_r:
            r_code = (
                f"try, run('{run_arg}'); catch e, " f"disp(getReport(e)); exit(1); end; exit(0);"
            )
            return [exe, "-wait", "-nosplash", "-nodesktop", "-r", r_code], "r"
        return [exe, "-batch", f"run('{run_arg}')"], "batch"

    # Linux / macOS: stdin-redirected
    return [exe, "-nojvm", "-nosplash", "-nodisplay"], "stdin"


def _glob_program_files() -> list[Path]:
    """Glob C:\\Program Files\\MATLAB\\R20*\\bin\\matlab.exe on Windows."""
    if os.name != "nt":
        return []
    out: list[Path] = []
    for base in ("C:/Program Files/MATLAB", "C:/Program Files (x86)/MATLAB"):
        for p in glob.glob(f"{base}/R20*/bin/matlab.exe"):
            out.append(Path(p))
    return sorted(out, reverse=True)  # newest first (lexical: R2025a > R2024b > R2024a)


def find_matlab_exe() -> Path:
    """Locate matlab.  MATLAB_EXE > PATH > Program Files."""
    env_val = os.environ.get("MATLAB_EXE")
    if env_val:
        p = Path(env_val)
        if p.exists():
            return p
    which = shutil.which("matlab") or shutil.which("matlab.exe")
    if which:
        return Path(which)
    for candidate in _glob_program_files():
        if candidate.exists():
            return candidate
    raise MatlabNotFoundError(
        "Cannot find 'matlab' on PATH. Set $MATLAB_EXE or install MATLAB "
        "R2023a+. See INSTALL.md for Windows-specific instructions."
    )


def _decode_matlab_output(raw: bytes) -> str:
    """Decode MATLAB console output to text.

    Tries UTF-8 first (strict), falls back to cp1252 on Windows and to the
    POSIX preferred encoding elsewhere. The fallback uses ``errors='replace'``
    so malformed bytes never raise; this matches the behaviour the callers
    expect when tailing a log file.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        fallback = "cp1252" if sys.platform == "win32" else locale.getpreferredencoding(False)
        return raw.decode(fallback, errors="replace")


def run_batch(
    script: Path,
    log: Path,
    matlab_exe: Path | None = None,
    fallback_r: bool = False,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> int:
    """Run a MATLAB script in batch mode; capture stdout+stderr to ``log``.

    Parameters
    ----------
    script, log
        Script to execute and path to write combined stdout/stderr to.
    matlab_exe
        Override the resolved matlab binary. Defaults to :func:`find_matlab_exe`.
    fallback_r
        Use the R2018a-compatible ``-r`` invocation (Windows only).
    env
        Full environment mapping to pass to ``subprocess.run``. When ``None``
        (the default) the child inherits ``os.environ`` via subprocess's
        default behaviour. Callers that need to add ``STAMPS`` or
        ``MATLABPATH`` should construct ``{**os.environ, "STAMPS": ...}``
        themselves and pass the merged dict here.
    cwd
        Working directory for the child process. Forwarded verbatim to
        ``subprocess.run``.
    timeout
        Seconds to wait before aborting. On timeout ``subprocess.run`` kills
        the MATLAB process and raises :class:`subprocess.TimeoutExpired`,
        which propagates out of this function unchanged.

    Raises
    ------
    RuntimeError
        If the environment variable ``STAMPS_SKIP_MATLAB=1`` was set at the
        time this module was imported. This is the CI / canary opt-out: it
        short-circuits before any subprocess is spawned.
    subprocess.TimeoutExpired
        If ``timeout`` is set and MATLAB does not exit in time. The child is
        killed by :mod:`subprocess` before the exception bubbles up.

    Notes
    -----
    Output from MATLAB on Windows can arrive as UTF-16LE, UTF-8, or cp1252
    depending on locale and whether ``-batch`` or ``-r`` is used. To keep
    the log file uniformly UTF-8 the raw bytes are buffered in memory,
    decoded (UTF-8 strict, then cp1252/locale fallback with
    ``errors='replace'``), and re-encoded as UTF-8 before being written.
    """
    if _SKIP_MATLAB:
        raise RuntimeError("MATLAB invocation skipped by STAMPS_SKIP_MATLAB=1")

    exe = matlab_exe or find_matlab_exe()
    cmd, mode = build_cmd(script, log, matlab_exe=exe, fallback_r=fallback_r)

    if sys.platform == "win32":
        print(f"Starting MATLAB (Windows cold start, ~10-15 s): {exe}", file=sys.stderr)

    if mode == "stdin":
        with open(script, "rb") as script_fh:
            proc = subprocess.run(
                cmd,
                stdin=script_fh,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                env=env,
                cwd=cwd,
                timeout=timeout,
            )
    else:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=env,
            cwd=cwd,
            timeout=timeout,
        )

    # Decode raw bytes (UTF-8 strict → cp1252/locale fallback) and re-encode
    # UTF-8 so the log file stays in a predictable encoding across platforms.
    raw = proc.stdout if proc.stdout is not None else b""
    text = _decode_matlab_output(raw)
    with open(log, "wb") as log_fh:
        log_fh.write(text.encode("utf-8"))

    return proc.returncode
