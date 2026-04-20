from __future__ import annotations

import os
import warnings
from pathlib import Path

import pytest

from stamps._paths import stamps_root, resolve_bin, check_locale, shared_python_path


def test_stamps_root_from_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STAMPS", str(tmp_path))
    assert stamps_root() == tmp_path


def test_stamps_root_missing_raises(monkeypatch):
    monkeypatch.delenv("STAMPS", raising=False)
    with pytest.raises(RuntimeError, match="STAMPS"):
        stamps_root()


def test_resolve_bin_linux_no_suffix(monkeypatch, tmp_path: Path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "calamp").write_text("")
    monkeypatch.setenv("STAMPS", str(tmp_path))
    got = resolve_bin("calamp", platform="linux")
    assert got.name == "calamp"


def test_resolve_bin_windows_prefers_exe(monkeypatch, tmp_path: Path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "calamp.exe").write_text("")
    monkeypatch.setenv("STAMPS", str(tmp_path))
    got = resolve_bin("calamp", platform="win32")
    assert got.name == "calamp.exe"


def test_resolve_bin_missing_raises(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STAMPS", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        resolve_bin("nonexistent_tool", platform="linux")


def test_locale_warning_on_comma_locale(monkeypatch):
    monkeypatch.setenv("LC_NUMERIC", "it_IT.UTF-8")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_locale()
    assert any("LC_NUMERIC" in str(x.message) for x in w)


def test_locale_silent_on_c(monkeypatch):
    monkeypatch.setenv("LC_NUMERIC", "C")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        check_locale()
    assert not [x for x in w if "LC_NUMERIC" in str(x.message)]


def test_shared_python_path_from_appdata(monkeypatch, tmp_path: Path):
    """PHASE may write %APPDATA%\\PHASE\\python.txt; honor it."""
    appdata = tmp_path / "AppData"; appdata.mkdir()
    phase_dir = appdata / "PHASE"; phase_dir.mkdir()
    (phase_dir / "python.txt").write_text("C:/Python311/python.exe")
    monkeypatch.setenv("APPDATA", str(appdata))
    assert shared_python_path() == Path("C:/Python311/python.exe")


def test_shared_python_path_missing_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert shared_python_path() is None
