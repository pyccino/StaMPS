"""End-to-end smoke: mt_prep_snap + stamps(1,7) on synthetic_ps_small fixture.

Nightly-tier (8-12 min wall-clock). Requires MATLAB license in CI.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.nightly
@pytest.mark.requires_matlab
def test_e2e_ps_pipeline(tmp_path: Path, stamps_root: Path):
    # 1. Copy fixture to tmp
    fixture_src = stamps_root / "tests" / "fixtures" / "synthetic_ps_small"
    if not fixture_src.exists():
        pytest.skip("synthetic_ps_small fixture not yet generated")
    shutil.copytree(fixture_src, tmp_path / "data", dirs_exist_ok=True)

    # 2. Run mt_prep_snap via shim
    shim_name = "mt_prep_snap.bat" if os.name == "nt" else "mt_prep_snap"
    shim = stamps_root / "bin" / shim_name
    proc = subprocess.run(
        [str(shim), "20200101", str(tmp_path / "data"),
         "0.4", "1", "1", "50", "50"],
        cwd=tmp_path, capture_output=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")

    # 3. Verify intermediate artifacts
    assert (tmp_path / "patch.list").exists()
    assert (tmp_path / "processor.txt").read_bytes() == b"snap\n"

    # 4. Run stamps(1,7) via _matlab helper
    from stamps._matlab import run_batch
    script = tmp_path / "run_stamps.m"
    script.write_text("stamps(1,7); exit(0);\n")
    rc = run_batch(script, tmp_path / "stamps.log")
    assert rc == 0, (tmp_path / "stamps.log").read_text(errors="replace")

    # 5. Expected .mat files
    expected = ("ps2.mat", "rc2.mat", "pm2.mat", "select2.mat",
                "weed2.mat", "phuw2.mat", "scla2.mat")
    for name in expected:
        assert (tmp_path / name).exists(), f"{name} not produced"

    # 6. Lightweight content sanity (scipy optional)
    try:
        from scipy.io import loadmat
    except ImportError:
        return
    ps2 = loadmat(tmp_path / "ps2.mat")
    n_ps = int(ps2["n_ps"][0][0])
    assert 10 < n_ps < 200, f"n_ps out of expected range [10..200]: {n_ps}"
