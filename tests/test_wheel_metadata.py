"""Wheel build smoke: verify pyproject metadata produces a sensible wheel."""
import subprocess
import sys
from pathlib import Path

import pytest


def test_wheel_builds_in_temp_dir(tmp_path: Path) -> None:
    """python -m build produces .whl + .tar.gz from current source tree."""
    repo_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
        cwd=repo_root, capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    wheels = list(tmp_path.glob("*.whl"))
    sdists = list(tmp_path.glob("*.tar.gz"))
    assert wheels, "no wheel produced"
    assert sdists, "no sdist produced"
