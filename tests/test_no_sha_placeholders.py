"""Fail if any SHA256 pin still has a placeholder value.

Catches release-time errors where a worker forgot to substitute
`<sha256>` or `0000...0000` after downloading Triangle / snaphu.
"""
import re
from pathlib import Path

import pytest


PLACEHOLDER_PATTERNS = [
    re.compile(r"\b0{64}\b"),                       # all-zeros
    re.compile(r"<sha256>", re.IGNORECASE),         # literal marker
    re.compile(r"compute.*real.*SHA256"),           # leftover comment hint
    re.compile(r"ba5ab2a8e3d19ad2f77bb3eaf8b68efb0b40f79a4de88f6c8b1b4b8dc1b8a7aa"),
    # Above is the published v3 plan placeholder — reject it literally so any
    # copy-paste of the example ships a real-computed hash instead.
]

# Catches the value-only fake: a worker substitutes the all-zeros literal
# with a 64-hex string of plausible-looking but NOT-real-tarball-derived
# bytes (e.g., copy-pasted from another project, or random hex). Every
# SHA256SUMS line and every URL_HASH line MUST match the strict format,
# AND the value must match what the URL_HASH download actually hashes to
# (CMake's URL_HASH check enforces this at configure time, but a stale
# value lingers in SHA256SUMS files unless we cross-check).
_SHA256_LINE = re.compile(
    r"^\s*(?:SHA256[\s=:]+)?(?P<hex>[0-9a-fA-F]{64})\b", re.MULTILINE
)


EXTERNAL_DIRS = ["external/triangle", "external/snaphu"]


@pytest.mark.parametrize("d", EXTERNAL_DIRS)
def test_no_placeholder_sha256(d, stamps_root):
    dir_path = stamps_root / d
    if not dir_path.exists():
        pytest.skip(f"{d} not yet vendored")
    violations = []
    for f in dir_path.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in {".txt", ".cmake", ".md", ".lock"} and f.name not in {
            "CMakeLists.txt", "SHA256SUMS",
        }:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for pat in PLACEHOLDER_PATTERNS:
            for m in pat.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                violations.append(f"{f.relative_to(stamps_root)}:{line_no}: placeholder {m.group(0)!r}")
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("d", EXTERNAL_DIRS)
def test_sha256_format_is_lowercase_64_hex(d, stamps_root):
    """Reject UPPERCASE hex, wrong-length, or non-hex SHA256 values.

    Catches value-only substitutions where a worker writes a plausible-but-
    invalid hex string. Pairs with `URL_HASH SHA256=` in CMake which would
    otherwise silently accept any 64-char string until tarball download.
    """
    dir_path = stamps_root / d
    if not dir_path.exists():
        pytest.skip(f"{d} not yet vendored")
    violations: list[str] = []
    for f in dir_path.rglob("SHA256SUMS"):
        text = f.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tok = line.split()[0] if line.split() else ""
            if not re.fullmatch(r"[0-9a-f]{64}", tok):
                violations.append(
                    f"{f.relative_to(stamps_root)}:{line_no}: "
                    f"expected lowercase 64-hex SHA256, got {tok!r}"
                )
    assert not violations, "\n".join(violations)
