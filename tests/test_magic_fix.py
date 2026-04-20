"""Magic constant must use int32_t, not long (cross-platform size differs).

On LP64 (Linux/macOS) `long` is 64-bit; on LLP64 (Win64/MSVC) it is 32-bit.
The Sun raster header magic field is a fixed 4-byte big-endian word, so the
type used to read/compare it must be an exact 32-bit integer — otherwise
the reinterpret_cast reads the wrong number of bytes on LP64.

The original three files (pscphase/pscdem/psclonlat) were fixed in an earlier
sweep; selpsc_patch and selsbc_patch were the real offenders addressed on
this branch. We guard all five to prevent regression in either direction.
"""

from pathlib import Path


def test_no_long_magic_in_psc_files(stamps_root: Path):
    for name in ("pscphase", "pscdem", "psclonlat", "selpsc_patch", "selsbc_patch"):
        text = (stamps_root / "src" / f"{name}.cpp").read_text()
        assert "long magic" not in text, f"{name}.cpp still uses long magic"
        assert "reinterpret_cast<long*>" not in text, f"{name}.cpp still casts via long*"
        assert (
            "int32_t" in text or "#include <cstdint>" in text
        ), f"{name}.cpp should use int32_t types"
