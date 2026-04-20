"""selsbc_patch main() must have an explicit `return 0;` for MSVC C4715."""

from pathlib import Path


def test_selsbc_has_explicit_return_zero(stamps_root: Path):
    text = (stamps_root / "src" / "selsbc_patch.cpp").read_text()
    # The explicit return 0 must appear (not commented-out).
    lines = [ln for ln in text.splitlines() if "return 0" in ln and not ln.strip().startswith("//")]
    assert lines, "No uncommented 'return 0' found in selsbc_patch.cpp"
