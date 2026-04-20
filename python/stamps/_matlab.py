"""Cross-platform MATLAB batch invocation for the StaMPS Python port.

.. note::

   ``STAMPS_SKIP_MATLAB`` is read at module import; changing it after import
   has no effect. Use ``importlib.reload(stamps._matlab)`` to pick up a new
   value.
"""

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
# The value is frozen at import: flipping the env var after import does not
# re-arm the guard. Callers needing dynamic behaviour must reload the module
# (``importlib.reload(stamps._matlab)``).
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


def _decode_matlab_output(raw: bytes) -> tuple[str, str]:
    """Decode MATLAB console output to text.

    Tries UTF-8 first (strict), falls back to cp1252 on Windows and to the
    POSIX preferred encoding elsewhere. The fallback uses ``errors='replace'``
    so malformed bytes never raise; this matches the behaviour the callers
    expect when tailing a log file.

    Returns
    -------
    tuple of (text, strategy)
        ``text`` is the decoded string; ``strategy`` is the codec name that
        actually produced it (``"utf-8"`` on clean decode, otherwise the
        fallback codec name such as ``"cp1252"`` or the POSIX preferred
        encoding). The caller uses ``strategy`` to annotate the log file so
        U+FFFD replacement characters can be traced back to the codec choice.
    """
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        fallback = "cp1252" if sys.platform == "win32" else locale.getpreferredencoding(False)
        return raw.decode(fallback, errors="replace"), fallback


def run_batch(
    script: Path,
    log: Path,
    matlab_exe: Path | None = None,
    fallback_r: bool = False,
    *,
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
    env : keyword-only
        Full environment mapping to pass to ``subprocess.run``. When ``None``
        (the default) the child inherits ``os.environ`` via subprocess's
        default behaviour. Callers that need to add ``STAMPS`` or
        ``MATLABPATH`` should construct ``{**os.environ, "STAMPS": ...}``
        themselves and pass the merged dict here.
    cwd : keyword-only
        Working directory for the child process. Forwarded verbatim to
        ``subprocess.run``.
    timeout : keyword-only
        Seconds to wait before aborting. On timeout ``subprocess.run`` kills
        the MATLAB process and raises :class:`subprocess.TimeoutExpired`,
        which propagates out of this function unchanged.

    ``env``, ``cwd``, and ``timeout`` are keyword-only to prevent accidental
    positional collisions with future additions to the signature.

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
    A single-line prelude (``# stamps: decoded via <codec>\\n``) is
    prepended to the log body so the codec choice is visible next to the
    decoded content during debugging.
    """
    if _SKIP_MATLAB:
        raise RuntimeError("MATLAB invocation skipped by STAMPS_SKIP_MATLAB=1")

    exe = matlab_exe or find_matlab_exe()
    cmd, mode = build_cmd(script, log, matlab_exe=exe, fallback_r=fallback_r)

    if sys.platform == "win32":
        print(f"Starting MATLAB (Windows cold start, ~10-15 s): {exe}", file=sys.stderr)

    # NOTE: stdout is buffered whole in memory (stdout=PIPE). MATLAB batch
    # output is typically kilobytes, rarely megabytes, so this is acceptable.
    # Streaming to the log file incrementally would require a background
    # thread (or selectors / async) to drain stdout and stderr concurrently
    # without deadlocking on full OS pipe buffers; simplicity wins here until
    # a concrete workload motivates the complexity.
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
    # Prepend a one-line prelude recording the codec that actually decoded
    # the bytes; without it, U+FFFD replacements in the log give no clue
    # whether UTF-8 or the fallback produced them.
    raw = proc.stdout if proc.stdout is not None else b""
    text, strategy = _decode_matlab_output(raw)
    prelude = f"# stamps: decoded via {strategy}\n"
    with open(log, "wb") as log_fh:
        log_fh.write((prelude + text).encode("utf-8"))

    return proc.returncode
