"""After PR1 rename, src/ must have exactly 13 .cpp, zero .c."""

from pathlib import Path


def test_all_c_files_are_cpp(stamps_root: Path):
    src = stamps_root / "src"
    assert not any(src.glob("*.c")), "No .c files should remain"
    cpp_count = len(list(src.glob("*.cpp")))
    assert cpp_count == 13, f"Expected 13 .cpp files, got {cpp_count}"


def test_seven_core_binaries_present(stamps_root: Path):
    src = stamps_root / "src"
    core = {"calamp", "cpxsum", "pscphase", "pscdem", "psclonlat", "selpsc_patch", "selsbc_patch"}
    for name in core:
        assert (src / f"{name}.cpp").exists(), f"Missing {name}.cpp"
