"""Environment + binary + shared-config resolution."""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path


def stamps_root() -> Path:
    val = os.environ.get("STAMPS")
    if not val:
        raise RuntimeError(
            "STAMPS environment variable is not set. Source "
            "StaMPS_CONFIG.bash (Linux) or StaMPS_CONFIG.ps1 (Windows)."
        )
    # resolve(strict=False) canonicalizes the path so callers that compare
    # two stamps_root()-derived paths dedupe across NTFS junctions and
    # symlinks. strict=False lets setup-time callers use this before the
    # target directory exists (some tests do this).
    return Path(val).resolve(strict=False)


def _paths_equivalent(a: Path, b: Path) -> bool:
    """Return True if *a* and *b* point at the same filesystem object.

    Uses ``os.path.samefile`` which compares inode (POSIX) / file-id
    (Windows) — reliable across NTFS junctions where ``Path.resolve``
    has historical edge cases. Falls back to ``resolve(strict=False)``
    equality when ``samefile`` raises ``FileNotFoundError`` (either
    operand doesn't exist on disk yet).
    """
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return a.resolve(strict=False) == b.resolve(strict=False)


def resolve_bin(name: str, platform: str | None = None) -> Path:
    plat = platform or sys.platform
    binroot = stamps_root() / "bin"
    candidates = [binroot / name]
    if plat == "win32":
        candidates.insert(0, binroot / f"{name}.exe")
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Cannot find StaMPS binary '{name}' in {binroot}. "
        f"Run cmake --build or download the release .zip."
    )


_COMMA_LOCALES = ("it_", "de_", "fr_", "es_", "pt_", "nl_", "ru_")


def check_locale() -> None:
    lc = os.environ.get("LC_NUMERIC", "")
    if any(lc.startswith(pfx) for pfx in _COMMA_LOCALES):
        warnings.warn(
            f"LC_NUMERIC={lc!r} uses comma as decimal separator. "
            "The Python port is locale-invariant, but some older MATLAB "
            "versions are not. See INSTALL.md for mitigations.",
            stacklevel=2,
        )


def shared_python_path() -> Path | None:
    """Check %APPDATA%\\PHASE\\python.txt for shared Python resolution.

    PHASE's setupPythonEnvironment.m writes the resolved interpreter path
    here so StaMPS can use the same one, avoiding PHASE/StaMPS dual-Python
    confusion on Windows.
    """
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    cfg = Path(appdata) / "PHASE" / "python.txt"
    if not cfg.exists():
        return None
    try:
        # utf-8-sig so a BOM written by a careless tool is stripped.
        text = cfg.read_text(encoding="utf-8-sig", errors="strict").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return Path(text) if text else None


def check_python_coordination() -> None:
    """Warn if PHASE's shared-config points to a different Python than ours."""
    shared = shared_python_path()
    if shared is None:
        return
    running = Path(sys.executable)
    try:
        if not _paths_equivalent(shared, running):
            warnings.warn(
                f"PHASE's %APPDATA%\\PHASE\\python.txt points to "
                f"{shared} but StaMPS is running under {running}. "
                f"Align via $env:STAMPS_PYTHON or re-run PHASE's "
                f"setupPythonEnvironment.m.",
                stacklevel=2,
            )
    except OSError:
        pass
