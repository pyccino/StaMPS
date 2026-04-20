"""Magic constant must use int32_t, not long (cross-platform size differs).

Windows LLP64 has sizeof(long) == 4, POSIX LP64 has sizeof(long) == 8 —
the Sun raster `magic` value MUST be declared and cast via a
fixed-width 32-bit type so header-matching works identically on both.
Scans ignore comments and string literals to avoid matching
`"long magic"` inside an error message or a `// long magic` remark.
"""

import re
from pathlib import Path


def _strip_cpp_non_code(src: str) -> str:
    # Assumes StaMPS src/ does NOT use C++11 raw-string literals R"(...)"
    # — their contents would leak through. Char literals ARE stripped so
    # a lone `'"'` can't unbalance the string-literal quote pairing.
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r"'(?:\\.|[^'\\])*'", "''", src)
    src = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
    return src


# Forbidden patterns — any one of these is a regression.
BAD_PATTERNS = [
    (re.compile(r"\blong\s+magic\b"), "scalar `long magic` declaration"),
    (re.compile(r"\blong\s+magic\s*\["), "array `long magic[...]` declaration"),
    (re.compile(r"reinterpret_cast\s*<\s*long\s*\*\s*>"), "`reinterpret_cast<long*>` cast"),
    (re.compile(r"\(\s*long\s*\*\s*\)"), "C-style `(long*)` cast"),
]


def test_no_long_magic_in_psc_files(stamps_root: Path):
    for name in ("pscphase", "pscdem", "psclonlat"):
        raw = (stamps_root / "src" / f"{name}.cpp").read_text()
        code = _strip_cpp_non_code(raw)
        for pattern, label in BAD_PATTERNS:
            m = pattern.search(code)
            assert m is None, f"{name}.cpp contains forbidden {label}: {m.group(0)!r}"
        # Positive check: int32_t must be present (use OR include counts).
        assert re.search(r"\bint32_t\b", code) or re.search(
            r"^\s*#\s*include\s*<cstdint>", code, re.MULTILINE
        ), f"{name}.cpp should use int32_t types"
