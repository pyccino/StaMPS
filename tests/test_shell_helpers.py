"""Tests for python/stamps/_shell.py."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from stamps._shell import (
    sorted_glob, rm_rf_glob, append_glob, mkdir_if_missing,
    write_text_lf, write_text_for_cpp, long_path,
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
    """On Windows paths > 240 chars get \\\\?\\ prefix; Linux unchanged."""
    long_name = "a" * 260
    p = Path(long_name)
    got = long_path(p)
    if os.name == "nt":
        assert str(got).startswith("\\\\?\\")
    else:
        assert got == p


def test_long_path_short_path_unchanged():
    p = Path("/tmp/short")
    assert long_path(p) == p
