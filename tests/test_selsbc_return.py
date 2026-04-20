"""selsbc_patch main() must have an explicit `return 0;` for MSVC C4715.

The scan strips comments and string literals, then looks for
`return 0;` inside the brace pair of `int main(...)`. Helper functions
returning 0 elsewhere in the file must not satisfy the check.
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


def _extract_main_body(code: str) -> str:
    """Return the contents of `int main(...) { ... }` with balanced braces.

    Raises AssertionError if `int main` is not found or braces don't balance.
    """
    m = re.search(r"\bint\s+main\s*\([^)]*\)\s*\{", code)
    assert m is not None, "No `int main(...) {` signature found"
    start = m.end() - 1  # position of the opening `{`
    depth = 0
    for i, ch in enumerate(code[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return code[start + 1 : i]
    raise AssertionError("Unbalanced braces in main()")


RETURN_ZERO_RE = re.compile(r"\breturn\s+0\s*;")


def test_selsbc_has_explicit_return_zero(stamps_root: Path):
    raw = (stamps_root / "src" / "selsbc_patch.cpp").read_text()
    code = _strip_cpp_non_code(raw)
    body = _extract_main_body(code)
    assert RETURN_ZERO_RE.search(body), (
        "No uncommented `return 0;` found inside main() of selsbc_patch.cpp "
        "(required for MSVC C4715)"
    )
