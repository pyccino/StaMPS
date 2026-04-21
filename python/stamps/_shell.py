"""Filesystem helpers for the StaMPS Python port.

Preserves csh semantics (sorted glob, LF-only writes, missing-ok rm) and
works identically on Linux, macOS, and Windows. Includes \\\\?\\ long-path
support on Windows, ANSI-code-page encoding for files consumed by C++
narrow-API ifstream.
"""

from __future__ import annotations

import glob as _glob
import locale
import os
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import overload


def _chmod_tree_writable(root: Path) -> None:
    """Walk *root* and restore owner-writable modes.

    Read-only directories block their own contents from being unlinked;
    read-only files resist unlink on Windows. Pre-walking is the most
    robust fix: by the time ``shutil.rmtree`` starts, every entry is
    already writable, so its ``onexc`` handler only needs to catch
    surprises (races, concurrent access). os.walk(topdown=True) lets us
    chmod a directory *before* we try to descend into it.

    Best-effort: chmod errors are swallowed. The subsequent rmtree will
    surface any genuine failure.
    """
    try:
        os.chmod(root, stat.S_IRWXU)
    except OSError:
        pass
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        for name in dirnames:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IRWXU)
            except OSError:
                pass
        for name in filenames:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IWRITE | stat.S_IREAD)
            except OSError:
                pass


def _force_remove(path: Path) -> None:
    """Remove a file or directory tree, tolerating read-only entries.

    Windows refuses to delete files flagged FILE_ATTRIBUTE_READONLY; the
    unlink/rmtree syscall raises PermissionError. The same trap exists
    on POSIX for read-only directories (missing owner-write bit): the
    dir's own entries cannot be unlinked until the dir itself has write.

    Strategy: pre-walk the tree and restore writable modes, then call
    rmtree. An ``onexc``/``onerror`` handler still runs as a safety net
    for races (a file becoming read-only between our pre-walk and
    rmtree's unlink). Symlinks are unlinked directly — never recursed
    into.

    Python 3.12 renamed ``shutil.rmtree(onerror=...)`` to
    ``shutil.rmtree(onexc=...)`` with a slightly different callback
    signature: ``onexc(func, path, exc)`` vs the legacy
    ``onerror(func, path, exc_info)``. Passing ``onerror=`` on 3.12+
    emits ``DeprecationWarning``, which breaks any CI that runs under
    ``filterwarnings = error``. Branch on version; share the body.
    """

    def _handler(func, p):  # type: ignore[no-untyped-def]
        mode = stat.S_IRWXU if os.path.isdir(p) else stat.S_IWRITE
        try:
            os.chmod(p, mode)
        except OSError:
            pass
        if func in (os.unlink, os.rmdir, os.remove):
            func(p)

    if path.is_dir() and not path.is_symlink():
        _chmod_tree_writable(path)
        if sys.version_info >= (3, 12):

            def onexc(func, p, _exc):  # type: ignore[no-untyped-def]
                _handler(func, p)

            shutil.rmtree(path, onexc=onexc)
        else:

            def onerror(func, p, _exc_info):  # type: ignore[no-untyped-def]
                _handler(func, p)

            shutil.rmtree(path, onerror=onerror)
    elif path.exists() or path.is_symlink():
        try:
            path.unlink()
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            path.unlink()


def sorted_glob(pattern: Path | str) -> list[Path]:
    """Glob a pattern (may be multi-component) and return sorted list.

    Uses stdlib `glob.glob` which handles arbitrary wildcards anywhere in
    the pattern. Returns [] on no match. Sort key is raw bytes (os.fsencode)
    to match Linux `\\ls` under LC_COLLATE=C, where `Z` < `a` in ASCII byte
    order. casefold() would be wrong — it's case-insensitive, LC_COLLATE=C
    is case-sensitive by raw byte.
    """
    matches = _glob.glob(str(long_path(pattern)))
    return sorted((Path(m) for m in matches), key=lambda p: os.fsencode(str(p)))


def rm_rf_glob(pattern: Path | str, retries: int = 3, backoff_s: float = 0.1) -> None:
    """Delete every path matching pattern, files or directories.

    Refuses to act on shallow patterns (< 3 path components resolved from
    filesystem root) to prevent catastrophic accidents. Relative patterns
    are resolved against Path.cwd() BEFORE the depth check, so a cwd of
    /home/user/project/run + pattern "PATCH_*" gets depth 4 (safe), while
    a cwd of /tmp + "PATCH_*" gets depth 2 (refused — callers should
    invoke from a deeper workdir).
    """
    p = Path(pattern)
    # Coerce to absolute first so the depth check is deterministic
    # regardless of whether caller passed relative or absolute pattern.
    if not p.is_absolute():
        p = Path.cwd() / p
    # Compute the pattern's base directory (longest path prefix with no wildcards)
    base_parts = []
    for part in p.parts:
        if any(ch in part for ch in "*?["):
            break
        base_parts.append(part)
    base = Path(*base_parts) if base_parts else Path(p.anchor or "/")
    # Depth check on BOTH the raw absolute base and its resolved form. resolve()
    # can lengthen a path via autofs/firmlinks (macOS `/home` → multi-level
    # synthetic mount under /System/Volumes/...) and mask an actually-shallow
    # pattern. Checking both the raw and resolved parts means we're never less
    # strict than the caller's literal intent.
    raw_parts = base.parts
    try:
        resolved_parts = base.resolve().parts
    except (OSError, RuntimeError):
        resolved_parts = raw_parts
    if len(raw_parts) < 3 or len(resolved_parts) < 3:
        raise ValueError(f"refusing to rm_rf_glob at shallow path (depth<3): {base}")

    for victim in sorted_glob(p):
        for attempt in range(retries):
            try:
                _force_remove(victim)
                break
            except FileNotFoundError:
                # Matches the prior unlink(missing_ok=True) contract.
                break
            except PermissionError:
                if attempt == retries - 1:
                    raise
                time.sleep(backoff_s)


def mkdir_if_missing(d: Path | str, retries: int = 3, backoff_s: float = 0.1) -> None:
    """Create directory if missing. Idempotent. Retries on PermissionError."""
    p = long_path(Path(d))
    for attempt in range(retries):
        try:
            p.mkdir(parents=True, exist_ok=True)
            return
        except PermissionError:
            if attempt == retries - 1:
                raise
            time.sleep(backoff_s)


_ONEDRIVE_BACKOFF_SCHEDULE_S = (0.1, 0.25, 0.6, 1.5, 2.5)
"""Exponential backoff schedule (seconds) for PermissionError retries.

OneDrive sync locks observed in the field hold for 1–2 s. Total budget is
~4.85 s — enough to ride out one full sync cycle without making CI hang
forever on a genuinely unwritable path. Five attempts, not three.
"""


def _write_bytes_with_retry(
    path: Path,
    data: bytes,
    schedule_s: tuple[float, ...] = _ONEDRIVE_BACKOFF_SCHEDULE_S,
    mode: str = "wb",
) -> None:
    """write_bytes/append with PermissionError retry (OneDrive sync lock mitigation).

    Sleeps schedule_s[attempt] before each retry. Re-raises after the
    final attempt so genuine permission errors still surface.

    ``mode`` is either ``"wb"`` (truncate-and-write, default) or ``"ab"``
    (binary append). Only binary modes are accepted — text-mode writes
    would defeat the LF-only invariant this module enforces on Windows.
    """
    if mode not in ("wb", "ab"):
        raise ValueError(f"_write_bytes_with_retry: mode must be 'wb' or 'ab', got {mode!r}")
    p = long_path(path)
    last_exc: PermissionError | None = None
    for attempt, delay in enumerate(schedule_s):
        try:
            if mode == "wb":
                p.write_bytes(data)
            else:
                with open(p, "ab") as fh:
                    fh.write(data)
            return
        except PermissionError as e:
            last_exc = e
            if attempt < len(schedule_s) - 1:
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def write_text_lf(path: Path | str, content: str) -> None:
    """Write text with LF endings and UTF-8 encoding on every OS.

    Byte-identical to the prior ASCII encoder for the ASCII subset, so
    existing csh-captured goldens don't drift. UTF-8 was chosen over
    strict ASCII because SNAP-provided fields (orbit product names,
    mission labels) may carry occasional non-ASCII whitespace; downstream
    StaMPS C++ binaries treat the file contents as opaque byte streams
    plus newline delimiters, so UTF-8 passthrough is safe. Retries on
    PermissionError (OneDrive sync lock). Uses \\\\?\\ long-path prefix on
    Windows paths > 240 chars.
    """
    _write_bytes_with_retry(Path(path), content.encode("utf-8"))


def append_text_lf(path: Path | str, text: str) -> None:
    """Append text to a file with LF-only endings on every OS.

    Opens the file in binary-append mode ("ab") and writes UTF-8-encoded
    bytes so Windows text-mode newline translation can never introduce
    \\r\\n into a file written by `write_text_lf()`. Creates the file if
    it does not yet exist. Uses \\\\?\\ long-path prefix on Windows paths
    > 240 chars. Retries on PermissionError (OneDrive sync lock) through
    the shared `_write_bytes_with_retry` helper.

    This is the append counterpart to `write_text_lf()` — use it instead
    of `open(path, "a")` whenever a file must stay LF-only.
    """
    _write_bytes_with_retry(Path(path), text.encode("utf-8"), mode="ab")


def write_text_for_cpp(path: Path | str, content: str) -> None:
    """Write a text file that downstream C++ ifstream(const char*) can open.

    On Windows, narrow-API CreateFileA interprets paths via the ANSI code
    page. ASCII content is invariant; non-ASCII is encoded via
    `locale.getpreferredencoding()`. Retries on PermissionError.
    """
    encoding = locale.getpreferredencoding(False) if os.name == "nt" else "utf-8"
    normalized = content.replace("\r\n", "\n")
    _write_bytes_with_retry(Path(path), normalized.encode(encoding, errors="replace"))


def append_glob(out_path: Path | str, pattern: Path | str, preamble: str | None = None) -> None:
    """Append sorted glob matches (one per line, LF) to out_path."""
    out = long_path(Path(out_path))
    existing = out.read_bytes() if out.exists() else b""
    body_lines = [str(p) for p in sorted_glob(pattern)]
    body = ("\n".join(body_lines) + "\n") if body_lines else ""
    if preamble is not None and not existing:
        _write_bytes_with_retry(out, (preamble.rstrip("\n") + "\n" + body).encode("ascii"))
    else:
        _write_bytes_with_retry(out, existing + body.encode("ascii"))


@overload
def long_path(p: Path) -> Path: ...
@overload
def long_path(p: str) -> Path | str: ...
def long_path(p: Path | str) -> Path | str:
    """On Windows, prepend \\\\?\\ to paths longer than 240 chars.

    Accepts ``str | Path`` filesystem paths only. URIs (``file://``,
    ``http://``, ``https://``) are not supported — callers must resolve
    those to filesystem paths before calling. As a defensive guard
    against URI-shaped strings leaking in, the URI is returned unchanged
    (as ``str``); the check MUST fire BEFORE ``Path()`` construction
    because ``WindowsPath("file:///C:/foo")`` destructively rewrites the
    URI's forward slashes to backslashes — impossible to recover from
    after the fact.

    Allows CreateFileW-based APIs (Python's pathlib on Windows uses wide API)
    to exceed the 260-char MAX_PATH limit. On non-Windows, returns as-is.

    Normalizes forward slashes to backslashes on Windows before the UNC
    prefix check so inputs like ``//server/share/...`` are rewritten as
    ``\\\\?\\UNC\\server\\share\\...``. Python's ``pathlib`` plus user
    code frequently hand us mixed-separator strings on Windows; the
    \\\\?\\ prefix requires native backslashes.
    """
    if isinstance(p, str) and p.startswith(("file:", "http:", "https:", "\\\\?\\")):
        return p
    p = Path(p)
    if os.name != "nt":
        return p
    # Normalize forward slashes so UNC detection (\\) matches //server/share
    # and the final long-path prefix is well-formed (Windows \\?\ only
    # accepts backslash separators).
    s = str(p).replace("/", "\\")
    if len(s) < 240:
        return p
    # Absolute paths only (relative paths can't use \\?\ prefix)
    if not p.is_absolute():
        return p
    if s.startswith("\\\\"):  # UNC
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)
