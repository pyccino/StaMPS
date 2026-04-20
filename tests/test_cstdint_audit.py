"""Every .cpp using int*_t types must include <cstdint> directly.

The scan ignores C++ comments and string literals so that the use/include
check only fires on live source tokens — no false positives from
`cout << "int32_t"` strings or `// include <cstdint>` comments, and no
false negatives from `#include <cstdint>` hiding inside a macro body that
the naive substring check also didn't inspect.
"""

import re
from pathlib import Path

INT_TYPE_RE = re.compile(r"\b(u?int(8|16|32|64)_t)\b")
CSTDINT_INCLUDE_RE = re.compile(r"^\s*#\s*include\s*<cstdint>", re.MULTILINE)


def _strip_cpp_non_code(src: str) -> str:
    """Remove C/C++ block comments, line comments, and string/char literals.

    The result preserves line structure and whitespace enough for
    line-anchored regexes (e.g., `#include <cstdint>` on its own line)
    to still match. String and character literal contents are blanked so
    that tokens like `int32_t` or `<cstdint>` hidden inside a literal do
    not satisfy the use- or include- checks.

    Assumptions (StaMPS src/ satisfies both today):
      * No C++11 raw-string literals `R"(...)"` — those are NOT stripped
        and their contents would leak through. Audit this helper if raw
        strings are introduced.
      * Ordinary char literals like `'{'` or `'"'` ARE stripped, to avoid
        a stray `'"'` breaking the string-literal regex's quote pairing.
    """
    # Block comments first (non-greedy, dotall).
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    # Line comments.
    src = re.sub(r"//[^\n]*", "", src)
    # Character literals (handles backslash escapes) — must precede the
    # string-literal strip so a lone `'"'` doesn't unbalance quotes.
    src = re.sub(r"'(?:\\.|[^'\\])*'", "''", src)
    # String literals (handles backslash escapes).
    src = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
    return src


def test_cstdint_included_where_used(stamps_root: Path):
    offenders = []
    for cpp in (stamps_root / "src").glob("*.cpp"):
        raw = cpp.read_text()
        code = _strip_cpp_non_code(raw)
        uses_int_type = INT_TYPE_RE.search(code) is not None
        has_include = CSTDINT_INCLUDE_RE.search(code) is not None
        if uses_int_type and not has_include:
            offenders.append(cpp.name)
    assert not offenders, f"Files use int*_t without #include <cstdint>: {offenders}"
