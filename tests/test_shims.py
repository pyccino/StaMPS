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
def test_bat_rejects_microsoft_store_stub(stamps_root: Path, tmp_path: Path):
    """Regression guard for the \\WindowsApps\\ path sniff.

    We fake ``sys.executable`` by pointing STAMPS_PYTHON (via the shared
    PHASE config file) at a .bat that echoes a canned ``\\WindowsApps\\``
    path when called with ``-c "import sys; print(sys.executable)"``. The
    shim's for-/f resolver captures that path, findstr detects the Store
    fragment, and the shim must exit 9 with a message mentioning the
    Store on stderr.
    """
    fake_py = tmp_path / "fake_python.bat"
    fake_py.write_text(
        "@echo off\r\n"
        "echo C:\\Program Files\\WindowsApps\\PythonSoftwareFoundation.Python.3.11_x64\\python.exe\r\n"
    )
    appdata = tmp_path / "appdata"
    (appdata / "PHASE").mkdir(parents=True)
    (appdata / "PHASE" / "python.txt").write_text(str(fake_py))

    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    env = os.environ.copy()
    env["APPDATA"] = str(appdata)
    proc = subprocess.run([str(shim)], capture_output=True, timeout=30, env=env)
    assert proc.returncode == 9, (
        f"expected exit 9 for Store stub, got {proc.returncode}; " f"stderr={proc.stderr!r}"
    )
    assert b"Microsoft Store" in proc.stderr or b"WindowsApps" in proc.stderr


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Windows shim")
def test_bat_passes_utf8_args(stamps_root: Path, tmp_path: Path):
    """Argv byte round-trip: non-ASCII argv must reach sys.argv as UTF-8.

    The shim's cmd.exe layer must not mangle UTF-8 argv. A loose "rc not
    in (9009, 9)" check passes even when cmd.exe delivers mojibake, so
    this test is strict: we point STAMPS_PYTHON at a stub .bat that
    forwards to a real Python one-liner writing ``sys.argv[1]`` encoded
    as UTF-8 to stderr. The shim's resolver runs, invokes the stub, and
    the stub's stderr must be byte-identical to the input path's UTF-8
    encoding. Any byte drift (codepage 437 mojibake, surrogate-escape
    reinterpretation, etc.) fails the assertion.

    The stub must itself dispatch `-c "import sys; print(sys.executable)"`
    queries (shim's resolver probe) and the `-m stamps.mt_prep_snap ARGS`
    delegation separately, so it branches on argv[0] / module flag.
    """
    import sys as _sys

    non_ascii = "cafe\u0301_\u5927\u962a"  # café_大阪 (NFD to dodge filesystem NFC)
    expected = non_ascii.encode("utf-8")
    real_py = _sys.executable

    # Stub: two dispatch branches.
    #   (1) `-c SNIPPET` (shim's resolver probe): forward verbatim to the
    #       real Python so RESOLVED_PY comes out non-empty and without
    #       `\WindowsApps\`, satisfying the stub guard.
    #   (2) `-m stamps.mt_prep_snap MASTER DATADIR` (shim's delegation):
    #       ignore the module, write argv-for-DATADIR (==%~4) as UTF-8
    #       bytes to stderr, exit 42. We skip the real mt_prep_snap so
    #       the test doesn't need fixtures.
    # Written as CRLF bytes because cmd.exe is finicky about bare-LF .bat
    # files; delayed expansion is REQUIRED for !errorlevel! propagation.
    stub_src = (
        "@echo off\r\n"
        "setlocal enabledelayedexpansion\r\n"
        'if /i "%~1"=="-c" (\r\n'
        f'    "{real_py}" %*\r\n'
        "    exit /b !errorlevel!\r\n"
        ")\r\n"
        'if /i "%~1"=="-m" (\r\n'
        f'    "{real_py}" -c "import sys; sys.stderr.buffer.write(sys.argv[1].encode(\'utf-8\')); sys.exit(42)" "%~4"\r\n'
        "    exit /b !errorlevel!\r\n"
        ")\r\n"
        "exit /b 1\r\n"
    )
    stub = tmp_path / "stub_python.bat"
    stub.write_bytes(stub_src.encode("utf-8"))

    appdata = tmp_path / "appdata"
    (appdata / "PHASE").mkdir(parents=True)
    (appdata / "PHASE" / "python.txt").write_text(str(stub))

    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    env = os.environ.copy()
    env["APPDATA"] = str(appdata)
    proc = subprocess.run(
        [str(shim), "20200101", non_ascii],
        capture_output=True,
        timeout=30,
        env=env,
    )
    # Stub forces exit 42 on the -m branch. 9009/9 means resolver failed.
    assert proc.returncode == 42, (
        f"stub never ran -m branch: rc={proc.returncode}, "
        f"stdout={proc.stdout!r}, stderr={proc.stderr!r}"
    )
    # Byte-exact: stderr must contain UTF-8 bytes of the input argv.
    # Any cmd.exe mojibake (e.g. é -> 0x82 on CP437) fails this.
    assert (
        proc.stderr == expected
    ), f"argv byte mismatch: expected {expected!r}, got {proc.stderr!r}"


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
    # its exit code. The shim probes us with `-c "import sys; print(...)"`
    # to detect Microsoft Store stubs, so the wrapper MUST dispatch -c to
    # the real Python (otherwise the probe gets empty stdout and the shim
    # bails before reaching the -m branch). The `if`-block needs delayed
    # expansion (!errorlevel! not %ERRORLEVEL%) — see the docstring above.
    wrapper = tmp_path / "python_wrapper.cmd"
    wrapper.write_text(
        "@echo off\r\n"
        "setlocal enabledelayedexpansion\r\n"
        'if /i "%~1"=="-c" (\r\n'
        f'    "{sys.executable}" %*\r\n'
        "    exit /b !errorlevel!\r\n"
        ")\r\n"
        f'"{sys.executable}" "{stub_script}"\r\n'
        "exit /b %ERRORLEVEL%\r\n",
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
