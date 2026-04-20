"""calamp.cpp must format calib_factor with explicit scientific/setprecision."""

from pathlib import Path


def test_calamp_uses_scientific_setprecision(stamps_root: Path):
    text = (stamps_root / "src" / "calamp.cpp").read_text()
    assert "std::scientific" in text
    assert "std::setprecision(7)" in text
    assert "#include <iomanip>" in text
