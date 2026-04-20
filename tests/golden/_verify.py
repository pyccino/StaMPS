"""Compare a regenerated golden tree against the committed one.

File-type rules:
- Text files (.txt, .in, .out, .list, .log) must be byte-identical.
- Integer binaries (.ij, .ij0, .ij.int) must be byte-identical (pixel
  coordinates — no float math upstream).
- Float32 binaries (.flt, .da, .hgt, .ph, .ll) compare ulp-tolerant
  with rtol=1e-6, atol=0 — matches AC4's policy for MSVC output.
  Last-bit drift between glibc versions (NixOS vs Ubuntu, or Ubuntu
  LTS across years) is expected and acceptable here; algorithmic
  drift is not.

Exit 0 if all passes, 1 on any mismatch. Prints one line per mismatch.
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

_TEXT_SUFFIXES = {".txt", ".in", ".out", ".list", ".log"}
_INT_BINARY_SUFFIXES = {".ij", ".ij0"}
_FLOAT_BINARY_SUFFIXES = {".flt", ".da", ".hgt", ".ph", ".ll"}

_RTOL = 1e-6
_ATOL = 0.0


def _classify(path: Path) -> str:
    # .ij.int is an integer binary (compound suffix that Path.suffix won't
    # catch: Path("pscands.1.ij.int").suffix == ".int").
    if path.name.endswith(".ij.int"):
        return "int_binary"
    # .base files are gamma baseline text (human-readable).
    if path.suffix == ".base":
        return "text"
    s = path.suffix.lower()
    if s in _TEXT_SUFFIXES:
        return "text"
    if s in _INT_BINARY_SUFFIXES:
        return "int_binary"
    if s in _FLOAT_BINARY_SUFFIXES:
        return "float_binary"
    return "byte_exact"  # conservative default


def _byte_equal(a: bytes, b: bytes) -> bool:
    return hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def _ulp_compare_float32(a_bytes: bytes, b_bytes: bytes) -> tuple[bool, str]:
    if len(a_bytes) != len(b_bytes):
        return False, f"size differs: {len(a_bytes)} vs {len(b_bytes)}"
    if len(a_bytes) % 4 != 0:
        return False, "not float32-aligned"
    n = len(a_bytes) // 4
    a = struct.unpack(f"<{n}f", a_bytes)
    b = struct.unpack(f"<{n}f", b_bytes)
    worst_rel = 0.0
    worst_idx = -1
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        # NaN-safe: matching NaNs considered equal; mismatch otherwise.
        if x != x and y != y:
            continue
        if x != x or y != y:
            return False, f"NaN mismatch at index {i}: {x} vs {y}"
        diff = abs(x - y)
        tol = _ATOL + _RTOL * abs(y)
        if diff > tol:
            rel = diff / abs(y) if y != 0 else diff
            if rel > worst_rel:
                worst_rel = rel
                worst_idx = i
    if worst_idx >= 0:
        return False, f"worst drift: index {worst_idx} rel={worst_rel:.3e}"
    return True, ""


def compare_trees(
    committed: Path,
    fresh: Path,
    ignore_extras: set[str] | None = None,
) -> list[str]:
    """Compare committed golden tree against freshly produced tree.

    ignore_extras: basenames to accept as present in fresh but not in
    committed (e.g. run-local shims like 'matlab', or symlinks the test
    harness creates in the workdir). Files in committed but absent in
    fresh are ALWAYS flagged — they represent a regression in the port.
    """
    ignore_extras = ignore_extras or set()
    mismatches: list[str] = []
    missing: list[str] = []
    for src in sorted(committed.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(committed)
        actual = fresh / rel
        if not actual.exists():
            missing.append(str(rel))
            continue
        a_bytes = src.read_bytes()
        b_bytes = actual.read_bytes()
        kind = _classify(src)
        if kind == "float_binary":
            ok, reason = _ulp_compare_float32(a_bytes, b_bytes)
            if not ok:
                mismatches.append(f"{rel} [float ulp-tol]: {reason}")
        else:
            if not _byte_equal(a_bytes, b_bytes):
                mismatches.append(f"{rel} [{kind}]: byte mismatch")
    # Also flag fresh-only files — regression in either direction matters.
    committed_set = {p.relative_to(committed) for p in committed.rglob("*") if p.is_file()}
    fresh_set = {p.relative_to(fresh) for p in fresh.rglob("*") if p.is_file()}
    for extra in sorted(fresh_set - committed_set):
        # Skip any component that is an ignored basename (e.g. "matlab"
        # under the workdir root, or any nested file whose basename is
        # listed in ignore_extras).
        if extra.name in ignore_extras or any(part in ignore_extras for part in extra.parts):
            continue
        mismatches.append(f"{extra}: extra file in fresh tree (not in golden)")
    for m in missing:
        mismatches.append(f"{m}: missing from fresh tree")
    return mismatches


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: _verify.py <committed_dir> <fresh_dir>", file=sys.stderr)
        return 2
    committed = Path(sys.argv[1])
    fresh = Path(sys.argv[2])
    mismatches = compare_trees(committed, fresh)
    if mismatches:
        print(f"VERIFY FAILED ({len(mismatches)} issues):")
        for m in mismatches:
            print(f"  {m}")
        return 1
    print(
        f"VERIFY OK (all files match; {sum(1 for _ in committed.rglob('*') if _.is_file())} files)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
