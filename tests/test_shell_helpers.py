"""Tests for python/stamps/_shell.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from stamps._shell import (
    append_glob,
    long_path,
    mkdir_if_missing,
    rm_rf_glob,
    sorted_glob,
    write_text_for_cpp,
    write_text_lf,
)


def test_sorted_glob_alphabetical(tmp_path: Path):
    (tmp_path / "c.slc").touch()
    (tmp_path / "a.slc").touch()
    (tmp_path / "b.slc").touch()
    result = sorted_glob(tmp_path / "*.slc")
    assert [p.name for p in result] == ["a.slc", "b.slc", "c.slc"]


def test_sorted_glob_no_match_returns_empty(tmp_path: Path):
    assert sorted_glob(tmp_path / "*.xyz") == []


def test_sorted_glob_multi_component_pattern(tmp_path: Path):
    """Regression: patterns like dir/*subdir/*.par must work."""
    (tmp_path / "xslc").mkdir()
    (tmp_path / "yslc").mkdir()
    (tmp_path / "xslc" / "a.rslc.par").touch()
    (tmp_path / "yslc" / "b.rslc.par").touch()
    result = sorted_glob(tmp_path / "*slc" / "*.rslc.par")
    assert len(result) == 2
    assert result[0].name == "a.rslc.par"


def test_sorted_glob_deep_multi_component(tmp_path: Path):
    """Regression: 3-level glob `a/*/c/*.ext` must work."""
    (tmp_path / "SMALL_BASELINES").mkdir()
    (tmp_path / "SMALL_BASELINES" / "20200101_20200113").mkdir()
    (tmp_path / "SMALL_BASELINES" / "20200101_20200113" / "20200101.rslc.par").touch()
    result = sorted_glob(tmp_path / "SMALL_BASELINES" / "*" / "20200101.rslc.par")
    assert len(result) == 1


def test_rm_rf_glob_removes_dirs_and_files(tmp_path: Path):
    (tmp_path / "PATCH_1").mkdir()
    (tmp_path / "PATCH_1" / "x.txt").touch()
    (tmp_path / "PATCH_2").mkdir()
    (tmp_path / "PATCH_notadir").touch()
    rm_rf_glob(tmp_path / "PATCH_*")
    assert list(tmp_path.iterdir()) == []


def test_rm_rf_glob_missing_ok(tmp_path: Path):
    rm_rf_glob(tmp_path / "nothing_*")


def test_rm_rf_glob_refuses_shallow_pattern():
    # Depth check: refuse anything at depth < 3 from filesystem root
    with pytest.raises(ValueError, match="refusing"):
        rm_rf_glob(Path("/") / "*")
    if os.name == "nt":
        with pytest.raises(ValueError):
            rm_rf_glob(Path("C:/") / "*")
        with pytest.raises(ValueError):
            rm_rf_glob(Path("C:/Users/*"))
    else:
        with pytest.raises(ValueError):
            rm_rf_glob(Path("/home") / "*")
        with pytest.raises(ValueError):
            rm_rf_glob(Path("/usr") / "*")


def test_append_glob_lf_only(tmp_path: Path):
    (tmp_path / "a.slc").touch()
    (tmp_path / "b.slc").touch()
    out = tmp_path / "calamp.in"
    append_glob(out, tmp_path / "*.slc")
    data = out.read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"\n")
    assert data.count(b"\n") == 2


def test_append_glob_preserves_existing(tmp_path: Path):
    out = tmp_path / "f.in"
    out.write_bytes(b"100\n")
    (tmp_path / "a.slc").touch()
    append_glob(out, tmp_path / "*.slc")
    lines = out.read_bytes().splitlines()
    assert lines[0] == b"100"
    assert b"a.slc" in lines[1]


def test_mkdir_if_missing_idempotent(tmp_path: Path):
    d = tmp_path / "PATCH_1"
    mkdir_if_missing(d)
    mkdir_if_missing(d)
    assert d.is_dir()


def test_write_text_lf(tmp_path: Path):
    f = tmp_path / "t.txt"
    write_text_lf(f, "line1\nline2\n")
    assert f.read_bytes() == b"line1\nline2\n"
    assert b"\r" not in f.read_bytes()


def test_write_text_for_cpp_ascii(tmp_path: Path):
    f = tmp_path / "calamp.in"
    write_text_for_cpp(f, "20200101.rslc\n")
    assert f.read_bytes() == b"20200101.rslc\n"


def test_path_with_spaces(tmp_path: Path):
    d = tmp_path / "has space"
    d.mkdir()
    (d / "a.slc").touch()
    result = sorted_glob(d / "*.slc")
    assert len(result) == 1


def test_long_path_prefix_windows(monkeypatch):
    """On Windows absolute paths > 240 chars get \\\\?\\ prefix; Linux unchanged."""
    # long_path() only prefixes ABSOLUTE paths — relative paths can't use
    # the \\\\?\\ prefix per Win32 semantics. Build an absolute path so the
    # prefix rule actually fires.
    if os.name == "nt":
        p = Path("C:\\") / ("a" * 260)
    else:
        p = Path("/") / ("a" * 260)
    got = long_path(p)
    if os.name == "nt":
        # Accept either \\?\ or //?/ — MinGW WindowsPath normalizes to
        # forward slashes when stringified; native Windows uses backslashes.
        s = str(got)
        assert s.startswith("\\\\?\\") or s.startswith(
            "//?/"
        ), f"Expected \\\\?\\ or //?/ prefix, got: {s!r}"
    else:
        assert got == p


def test_long_path_short_path_unchanged():
    p = Path("/tmp/short")
    assert long_path(p) == p


@pytest.mark.windows_only
def test_sorted_glob_case_insensitive_fs_windows(tmp_path: Path):
    """NTFS is case-insensitive by default. Two paths `Foo.txt` and `foo.txt`
    collapse to a single on-disk file, so sorted_glob must return exactly
    one match rather than two — otherwise downstream callers that expect
    distinct entries (e.g. calamp_format) will double-process the same
    physical file.
    """
    (tmp_path / "Foo.txt").write_bytes(b"first")
    # On NTFS, this either overwrites the existing file or errors; either
    # way the final directory contains ONE file.
    try:
        (tmp_path / "foo.txt").write_bytes(b"second")
    except OSError:
        # Some NTFS configurations raise on case-variant create; ignore.
        pass
    result = sorted_glob(tmp_path / "*.txt")
    assert len(result) == 1, f"expected 1 entry on case-insensitive FS, got {result!r}"


def test_write_text_for_cpp_handles_non_ascii_path(tmp_path: Path):
    """Paths with non-ASCII components (e.g. user directory `café/`) must
    round-trip through write_text_for_cpp. The C++ ifstream consumes the
    file content byte-for-byte; the path itself is opened by Python (wide
    API on Windows, UTF-8 on POSIX), so unicode in the path is fine as
    long as write_bytes doesn't choke on the encoding of the content.
    """
    subdir = tmp_path / "café"
    subdir.mkdir()
    target = subdir / "calamp.in"
    write_text_for_cpp(target, "data")
    # Readback must equal the written payload. ASCII content is invariant
    # across locale.getpreferredencoding() on any OS.
    assert target.read_bytes() == b"data"
