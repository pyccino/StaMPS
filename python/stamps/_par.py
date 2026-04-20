"""Parser for SNAP / GAMMA / ROI_PAC .par-style key:value text files.

Replaces csh `gawk '/azimuth_lines/ {print $2}' < $RSC` idioms. Values
are parsed with Python's built-in int/float (locale-invariant). BOM is
stripped; CRLF tolerated; first occurrence of duplicate key wins
(matches csh backtick + word-split semantics).
"""
from __future__ import annotations

import re
from pathlib import Path


class ParError(RuntimeError):
    """Raised when a .par file cannot be read."""


_KV_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


def parse_par(path: Path | str) -> dict[str, int | float | str]:
    """Parse a .par file into a dict of typed values."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ParError(f"cannot read par file {p}: {exc}") from exc

    result: dict[str, int | float | str] = {}
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("#", "%")):
            continue
        m = _KV_RE.match(line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        if key in result:
            continue  # first-wins
        result[key] = _coerce(raw)
    return result


def _coerce(raw: str) -> int | float | str:
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
