from __future__ import annotations

import warnings
from pathlib import Path
from unittest import mock

import pytest
from stamps._paths import (
    _paths_equivalent,
    check_locale,
    resolve_bin,
    shared_python_path,
    stamps_root,
)


def test_stamps_root_from_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STAMPS", str(tmp_path))
    # stamps_root() canonicalizes via .resolve(strict=False); compare against
    # the same canonicalization so macOS (/tmp -> /private/tmp) still passes.
    assert stamps_root() == tmp_path.resolve(strict=False)


def test_stamps_root_missing_raises(monkeypatch):
    monkeypatch.delenv("STAMPS", raising=False)
    with pytest.raises(RuntimeError, match="STAMPS"):
        stamps_root()


def test_stamps_root_resolves_nonexistent_gracefully(monkeypatch, tmp_path: Path):
    """stamps_root() must not raise when STAMPS points at a path that
    does not exist yet — some callers/tests use it before the tree is
    created on disk."""
    target = tmp_path / "not-yet"
    assert not target.exists()
    monkeypatch.setenv("STAMPS", str(target))
    got = stamps_root()
    assert got == target.resolve(strict=False)
    # still must not exist — resolve(strict=False) doesn't create anything.
    assert not got.exists()


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
    appdata = tmp_path / "AppData"
    appdata.mkdir()
    phase_dir = appdata / "PHASE"
    phase_dir.mkdir()
    (phase_dir / "python.txt").write_text("C:/Python311/python.exe")
    monkeypatch.setenv("APPDATA", str(appdata))
    assert shared_python_path() == Path("C:/Python311/python.exe")


def test_shared_python_path_missing_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert shared_python_path() is None


def test_paths_equivalent_same_real_file(tmp_path: Path):
    """Two Path objects pointing at the same real file are equivalent."""
    f = tmp_path / "real"
    f.write_text("")
    assert _paths_equivalent(f, Path(str(f)))


def test_paths_equivalent_different_files(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text("")
    b.write_text("")
    assert not _paths_equivalent(a, b)


def test_paths_equivalent_falls_back_when_missing(tmp_path: Path):
    """If either operand does not exist, samefile raises FileNotFoundError;
    the helper must fall back to resolve()-based equality and not propagate."""
    missing_a = tmp_path / "nope-a"
    missing_b = tmp_path / "nope-b"
    assert not missing_a.exists()
    assert not missing_b.exists()
    assert _paths_equivalent(missing_a, missing_a)
    assert not _paths_equivalent(missing_a, missing_b)


@pytest.mark.windows_only
def test_paths_samefile_junction_windows(tmp_path: Path):
    """On Windows, an NTFS junction and its target must compare equivalent
    via _paths_equivalent. Creating a junction requires cmd's mklink /J."""
    import subprocess

    target = tmp_path / "target"
    target.mkdir()
    (target / "marker").write_text("x")
    junction = tmp_path / "junction"
    # mklink /J is a cmd builtin; must be invoked via cmd /c.
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"mklink /J failed (need admin or dev-mode?): {result.stderr}")
    assert _paths_equivalent(target, junction)
    assert _paths_equivalent(junction, target)


def test_paths_equivalent_calls_os_samefile(tmp_path: Path):
    """Contract test: the helper dispatches to os.path.samefile so it
    benefits from file-id semantics on NTFS junctions (which this Linux
    host cannot exercise directly)."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text("")
    b.write_text("")
    with mock.patch("stamps._paths.os.path.samefile", return_value=True) as sf:
        assert _paths_equivalent(a, b) is True
        sf.assert_called_once_with(a, b)
