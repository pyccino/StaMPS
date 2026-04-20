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
