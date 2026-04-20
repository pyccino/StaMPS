"""Magic constant must use int32_t, not long (cross-platform size differs)."""

from pathlib import Path


def test_no_long_magic_in_psc_files(stamps_root: Path):
    for name in ("pscphase", "pscdem", "psclonlat"):
        text = (stamps_root / "src" / f"{name}.cpp").read_text()
        assert "long magic" not in text, f"{name}.cpp still uses long magic"
        assert "reinterpret_cast<long*>" not in text, f"{name}.cpp still casts via long*"
        assert (
            "int32_t" in text or "#include <cstdint>" in text
        ), f"{name}.cpp should use int32_t types"
