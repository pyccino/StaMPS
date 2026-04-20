"""Tests for python/stamps/_matlab.py."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock, patch

import pytest
from stamps._matlab import (
    MatlabNotFoundError,
    build_cmd,
    escape_matlab_string,
    find_matlab_exe,
    run_batch,
)


def test_escape_matlab_string_doubles_apostrophe():
    assert escape_matlab_string("Bob's") == "Bob''s"
    assert escape_matlab_string("no quotes") == "no quotes"


def test_build_cmd_linux_stdin():
    # PurePosixPath pins forward-slash semantics regardless of host OS —
    # Path() on Windows would produce backslashes and break the test.
    cmd, mode = build_cmd(
        PurePosixPath("/tmp/s.m"),
        PurePosixPath("/tmp/s.log"),
        platform="linux",
        matlab_exe=PurePosixPath("/usr/bin/matlab"),
    )
    assert cmd[0] == "/usr/bin/matlab"
    assert "-batch" not in cmd
    assert mode == "stdin"


def test_build_cmd_windows_batch():
    cmd, mode = build_cmd(
        PureWindowsPath("C:/tmp/s.m"),
        PureWindowsPath("C:/tmp/s.log"),
        platform="win32",
        matlab_exe=PureWindowsPath("matlab.exe"),
    )
    assert "-batch" in cmd
    assert "run('C:/tmp/s.m')" in cmd[-1] or "run('C:\\tmp\\s.m')" in cmd[-1]
    assert mode == "batch"


def test_build_cmd_windows_unc_preserved():
    cmd, _ = build_cmd(
        PureWindowsPath(r"\\server\share\s.m"),
        PureWindowsPath(r"\\server\share\s.log"),
        platform="win32",
        matlab_exe=PureWindowsPath("matlab.exe"),
    )
    # UNC should pass as \\server\share\s.m (backslashes preserved)
    assert r"\\server\share\s.m" in cmd[-1] or "//server/share/s.m" in cmd[-1]


def test_build_cmd_windows_apostrophe_escaped():
    cmd, _ = build_cmd(
        PureWindowsPath("C:/Bob's/s.m"),
        PureWindowsPath("C:/Bob's/s.log"),
        platform="win32",
        matlab_exe=PureWindowsPath("matlab.exe"),
    )
    # Apostrophe in path must be doubled for MATLAB string literal
    assert "Bob''s" in cmd[-1]


def test_build_cmd_r2016a_fallback():
    cmd, mode = build_cmd(
        Path("C:/s.m"),
        Path("C:/s.log"),
        platform="win32",
        matlab_exe=Path("matlab.exe"),
        fallback_r=True,
    )
    assert "-r" in cmd
    assert "-batch" not in cmd
    assert mode == "r"
    # Must include exit(0)/exit(1) discipline
    assert "exit(0)" in cmd[-1] or "exit(1)" in cmd[-1]


def test_find_matlab_from_env(monkeypatch, tmp_path: Path):
    fake = tmp_path / "matlab"
    fake.write_text("#!/bin/sh")
    fake.chmod(0o755)
    monkeypatch.setenv("MATLAB_EXE", str(fake))
    assert find_matlab_exe() == fake


def test_find_matlab_via_which(monkeypatch, tmp_path: Path):
    fake = tmp_path / "matlab"
    fake.write_text("")
    fake.chmod(0o755)
    monkeypatch.delenv("MATLAB_EXE", raising=False)
    with patch("shutil.which", return_value=str(fake)):
        assert find_matlab_exe() == fake


def test_find_matlab_raises_on_missing(monkeypatch):
    monkeypatch.delenv("MATLAB_EXE", raising=False)
    with (
        patch("shutil.which", return_value=None),
        patch("stamps._matlab._glob_program_files", return_value=[]),
    ):
        with pytest.raises(MatlabNotFoundError, match="INSTALL.md"):
            find_matlab_exe()


def test_run_batch_exit_code_propagates(tmp_path: Path):
    script = tmp_path / "s.m"
    script.write_text("exit(3)")
    log = tmp_path / "s.log"
    mock_proc = MagicMock(returncode=3, stdout=b"", stderr=b"")
    with patch("subprocess.run", return_value=mock_proc):
        rc = run_batch(script, log, matlab_exe=Path("/fake/matlab"))
    assert rc == 3
