"""Tests for python/stamps/_matlab.py."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock, patch

import pytest
import stamps._matlab as matlab_mod
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


def test_run_batch_propagates_env(tmp_path: Path):
    """Caller-supplied env dict must reach subprocess.run verbatim."""
    script = tmp_path / "s.m"
    script.write_text("disp('hi')")
    log = tmp_path / "s.log"
    mock_proc = MagicMock(returncode=0, stdout=b"hi\n", stderr=b"")
    fake_env = {"STAMPS": "/fake", "MATLABPATH": "/fake/matlab"}
    with patch("stamps._matlab.subprocess.run", return_value=mock_proc) as mock_run:
        run_batch(script, log, matlab_exe=Path("/fake/matlab"), env=fake_env)
    assert mock_run.call_count == 1
    kwargs = mock_run.call_args.kwargs
    assert kwargs["env"] == fake_env
    assert kwargs["env"]["STAMPS"] == "/fake"


def test_run_batch_propagates_cwd(tmp_path: Path):
    """Caller-supplied cwd must reach subprocess.run verbatim."""
    script = tmp_path / "s.m"
    script.write_text("disp('hi')")
    log = tmp_path / "s.log"
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    mock_proc = MagicMock(returncode=0, stdout=b"", stderr=b"")
    with patch("stamps._matlab.subprocess.run", return_value=mock_proc) as mock_run:
        run_batch(script, log, matlab_exe=Path("/fake/matlab"), cwd=workdir)
    assert mock_run.call_args.kwargs["cwd"] == workdir


def test_run_batch_respects_timeout(tmp_path: Path):
    """subprocess.TimeoutExpired must propagate out of run_batch unchanged."""
    script = tmp_path / "s.m"
    script.write_text("while true; end")
    log = tmp_path / "s.log"
    err = subprocess.TimeoutExpired(cmd=["matlab"], timeout=0.1)
    with patch("stamps._matlab.subprocess.run", side_effect=err):
        with pytest.raises(subprocess.TimeoutExpired):
            run_batch(script, log, matlab_exe=Path("/fake/matlab"), timeout=0.1)


def test_run_batch_skips_when_stamps_skip_matlab_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Setting STAMPS_SKIP_MATLAB=1 and reimporting makes run_batch raise
    RuntimeError before any subprocess call is made."""
    monkeypatch.setenv("STAMPS_SKIP_MATLAB", "1")
    reloaded = importlib.reload(matlab_mod)
    script = tmp_path / "s.m"
    script.write_text("disp('hi')")
    log = tmp_path / "s.log"
    with patch("stamps._matlab.subprocess.run") as mock_run:
        with pytest.raises(RuntimeError, match="STAMPS_SKIP_MATLAB"):
            reloaded.run_batch(script, log, matlab_exe=Path("/fake/matlab"))
    assert mock_run.call_count == 0
    # Reset module state so other tests aren't poisoned by the skip flag.
    monkeypatch.delenv("STAMPS_SKIP_MATLAB", raising=False)
    importlib.reload(matlab_mod)


@pytest.mark.windows_only
def test_run_batch_decodes_cp1252_windows_fallback(tmp_path: Path):
    """Bytes that fail UTF-8 decode should be decoded via cp1252 on Windows
    and the log file must end up as valid UTF-8 containing the decoded form."""
    script = tmp_path / "s.m"
    script.write_text("disp('x')")
    log = tmp_path / "s.log"
    # 0x92 is a cp1252 right single-quote (U+2019). It is an invalid UTF-8
    # continuation byte, so strict UTF-8 decode must fail and the cp1252
    # fallback must take over.
    raw = b"Bob\x92s output\r\n"
    mock_proc = MagicMock(returncode=0, stdout=raw, stderr=b"")
    with patch("stamps._matlab.subprocess.run", return_value=mock_proc):
        rc = run_batch(script, log, matlab_exe=Path("C:/fake/matlab.exe"))
    assert rc == 0
    written = log.read_bytes()
    # Must be decodable as UTF-8 and must contain the U+2019 glyph we
    # recovered from the cp1252 byte.
    assert "Bob\u2019s output" in written.decode("utf-8")
