"""Every .cpp using int*_t types must include <cstdint> directly."""
import re
from pathlib import Path


INT_TYPE_RE = re.compile(r"\b(u?int(8|16|32|64)_t)\b")


def test_cstdint_included_where_used(stamps_root: Path):
    offenders = []
    for cpp in (stamps_root / "src").glob("*.cpp"):
        text = cpp.read_text()
        if INT_TYPE_RE.search(text) and "<cstdint>" not in text:
            offenders.append(cpp.name)
    assert not offenders, f"Files use int*_t without #include <cstdint>: {offenders}"
