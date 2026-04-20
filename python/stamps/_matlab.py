"""Cross-platform MATLAB batch invocation for the StaMPS Python port."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


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


def run_batch(
    script: Path,
    log: Path,
    matlab_exe: Path | None = None,
    fallback_r: bool = False,
) -> int:
    """Run a MATLAB script in batch mode; capture stdout+stderr to log."""
    exe = matlab_exe or find_matlab_exe()
    cmd, mode = build_cmd(script, log, matlab_exe=exe, fallback_r=fallback_r)

    if sys.platform == "win32":
        print(f"Starting MATLAB (Windows cold start, ~10-15 s): {exe}", file=sys.stderr)

    with open(log, "wb") as log_fh:
        if mode == "stdin":
            with open(script, "rb") as script_fh:
                proc = subprocess.run(
                    cmd, stdin=script_fh, stdout=log_fh, stderr=subprocess.STDOUT, check=False
                )
        else:
            proc = subprocess.run(cmd, stdout=log_fh, stderr=subprocess.STDOUT, check=False)
    return proc.returncode
