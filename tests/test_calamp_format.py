"""calamp.cpp must format calib_factor with explicit scientific/setprecision.

Weak presence-of-substring checks miss regressions where the manipulators
live on the wrong stream (cout instead of parmfile) or far from the
write. We parse the stripped source to confirm that `std::scientific`
and `std::setprecision(7)` appear in the same streaming chain that writes
`calib_factor`.
"""

import re
from pathlib import Path


def _strip_cpp_non_code(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
    return src


# A single streaming statement is any run of characters from a stream
# name through the terminating `;`. We'll extract those and look for the
# specific manipulators + `calib_factor` in the SAME statement.
STREAM_STMT_RE = re.compile(r"\bparmfile\s*<<[^;]*;", re.DOTALL)


def test_calamp_uses_scientific_setprecision(stamps_root: Path):
    raw = (stamps_root / "src" / "calamp.cpp").read_text()
    code = _strip_cpp_non_code(raw)

    # The header is still required — <iomanip> provides setprecision.
    assert re.search(
        r"^\s*#\s*include\s*<iomanip>", code, re.MULTILINE
    ), "calamp.cpp must #include <iomanip> for std::setprecision"

    # Find the streaming statement(s) that write to `parmfile` AND
    # include `calib_factor`. Require std::scientific and
    # std::setprecision(7) to appear in that same statement.
    matching = [stmt for stmt in STREAM_STMT_RE.findall(code) if "calib_factor" in stmt]
    assert matching, "No `parmfile << ... calib_factor ...;` streaming statement found"

    offenders = []
    for stmt in matching:
        has_scientific = "std::scientific" in stmt
        has_setprec7 = re.search(r"std::setprecision\s*\(\s*7\s*\)", stmt) is not None
        if not (has_scientific and has_setprec7):
            offenders.append(stmt.strip())
    assert not offenders, (
        "calib_factor write must apply std::scientific and "
        f"std::setprecision(7) in the same streaming chain; offending "
        f"statements: {offenders}"
    )
