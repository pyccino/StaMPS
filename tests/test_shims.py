import os
import subprocess
from pathlib import Path

import pytest


def _shim_env(stamps_root: Path) -> dict[str, str]:
    """Propagate the ``stamps`` package on PYTHONPATH so the shim's spawned
    Python process can import it without pip-installing the package. The
    production .bat shim sets PYTHONPATH itself from %~dp0; the sh shim
    relies on the package being importable already, which is true when
    StaMPS is pip-installed but not in a raw checkout."""
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    py_dir = str(stamps_root / "python")
    env["PYTHONPATH"] = py_dir + (os.pathsep + prev if prev else "")
    return env


@pytest.mark.linux_only
@pytest.mark.skipif(os.name == "nt", reason="Linux shim")
def test_bash_shim_passes_args_through(stamps_root: Path):
    shim = stamps_root / "bin" / "mt_prep_snap"
    # Call with no args -> should exit 4 (usage)
    proc = subprocess.run(
        [str(shim)],
        capture_output=True,
        timeout=10,
        env=_shim_env(stamps_root),
    )
    assert proc.returncode == 4


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Windows shim")
def test_bat_shim_passes_args_through(stamps_root: Path):
    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    proc = subprocess.run([str(shim)], capture_output=True, timeout=30)
    assert proc.returncode == 4


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Windows shim")
def test_bat_shim_preserves_quoted_arg_with_spaces(stamps_root: Path, tmp_path: Path):
    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    data = tmp_path / "my data"
    data.mkdir()
    # Call with master + datadir-with-space; we only check argv passthrough.
    proc = subprocess.run([str(shim), "20200101", str(data)], capture_output=True, timeout=30)
    # May exit nonzero (empty datadir), but must NOT fail with 9009 "not found"
    assert proc.returncode != 9009


def test_shim_propagates_exit_code(stamps_root: Path):
    shim_name = "mt_prep_snap.bat" if os.name == "nt" else "mt_prep_snap"
    shim = stamps_root / "bin" / shim_name
    # Insufficient args -> Python exits 4 -> shim must exit 4 (not 0 or 1)
    kwargs: dict = dict(capture_output=True, timeout=30)
    if os.name != "nt":
        kwargs["env"] = _shim_env(stamps_root)
    proc = subprocess.run([str(shim), "20200101"], **kwargs)
    assert proc.returncode == 4


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Windows shim")
def test_bat_propagates_nonzero_exit_code(stamps_root: Path, tmp_path: Path):
    """Regression for commit 2683fe1: ``%ERRORLEVEL%`` inside an ``if (...)``
    block is expanded at parse-time, giving the pre-call value (usually 0).
    ``!ERRORLEVEL!`` with ``setlocal enabledelayedexpansion`` expands at
    runtime.

    Verifies arbitrary nonzero exit codes (not just 4-via-usage) propagate
    through the .bat shim. We point STAMPS_PYTHON at a wrapper .cmd that
    runs a stub Python script calling ``sys.exit(42)``. The shim must
    return exit 42 verbatim — not 0 (the parse-time bug) or 1 (generic
    failure). Exercises the ``!ERRORLEVEL!`` passthrough inside the
    ``if defined STAMPS_PYTHON (...)`` block.
    """
    import sys

    stub_script = tmp_path / "stub_exit42.py"
    stub_script.write_text("import sys\nsys.exit(42)\n", encoding="ascii")
    # Wrapper .cmd that invokes the real Python on our stub and propagates
    # its exit code. Uses %ERRORLEVEL% (parse-time) since the exit is at
    # top level, not inside an if/for block — parse-time expansion is
    # correct here. No setlocal needed.
    wrapper = tmp_path / "python_wrapper.cmd"
    wrapper.write_text(
        f'@echo off\r\n"{sys.executable}" "{stub_script}"\r\nexit /b %ERRORLEVEL%\r\n',
        encoding="ascii",
    )
    # The shim reads STAMPS_PYTHON from %APPDATA%\PHASE\python.txt. Point
    # APPDATA at tmp_path so we don't touch the real user profile.
    appdata = tmp_path / "appdata"
    (appdata / "PHASE").mkdir(parents=True)
    (appdata / "PHASE" / "python.txt").write_text(str(wrapper), encoding="ascii")

    env = os.environ.copy()
    env["APPDATA"] = str(appdata)

    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    proc = subprocess.run(
        [str(shim), "20200101", str(tmp_path)],
        capture_output=True,
        timeout=30,
        env=env,
    )
    # If the shim regresses to parse-time %ERRORLEVEL%, we'd see 0. If it
    # somehow bypasses STAMPS_PYTHON and falls back to `py`/`python` on
    # PATH, we'd see 4 (usage). Require exactly 42 — the stub's exit code.
    assert proc.returncode == 42, (
        f"Expected exit 42 from stub, got {proc.returncode}. "
        f"If 0: !ERRORLEVEL! parse-time bug regressed. "
        f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
    )
