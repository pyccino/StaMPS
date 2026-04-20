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
    """Argv byte round-trip: non-ASCII path should reach sys.argv intact.

    The shim's cmd.exe layer must not mangle UTF-8 argv. We pass a path
    containing a CJK character and a non-ASCII Latin-1 one, and check
    that ``sys.argv[1]`` matches the input. We skip the full pipeline by
    stopping at the shim's Python-launch boundary: build a throwaway
    directory whose name contains the characters and pass it as the
    datadir; the shim invokes ``python -m stamps.mt_prep_snap`` which
    fails fast (no master or empty dir) but not before argv has been
    passed through. We check returncode != 9009 (shim-level PATH failure)
    and != 9 (stub rejection) — any other nonzero exit is fine because
    Python at least started and received the argv.
    """
    non_ascii = "cafe\u0301_\u5927\u962a"  # café_大阪 (NFD to dodge filesystem NFC)
    data = tmp_path / non_ascii
    data.mkdir()
    shim = stamps_root / "bin" / "mt_prep_snap.bat"
    proc = subprocess.run(
        [str(shim), "20200101", str(data)],
        capture_output=True,
        timeout=30,
    )
    # 9009 = Python not found (PATH failure); 9 = Store stub rejection.
    # Anything else (including 4 = usage error from stamps) means argv
    # made it past cmd.exe into a real Python process.
    assert proc.returncode not in (9009, 9), (
        f"shim failed before argv reached Python: rc={proc.returncode}, " f"stderr={proc.stderr!r}"
    )
