"""Drives PHASE → StaMPS end-to-end.

Calls PHASE's `run_stamps.m` (the function PHASE_StaMPS.mlapp invokes
internally) against a sentinel SLC fixture. Verifies that PHASE composes
the correct shell-out, the .bat shim launches Python, Python launches
MATLAB, and StaMPS produces the expected first-stage outputs.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.windows_only
@pytest.mark.requires_matlab
@pytest.mark.nightly
def test_phase_drives_stamps_end_to_end(tmp_path: Path):
    # Both env vars must be set; skip cleanly if the test is collected in
    # an environment that doesn't point at a PHASE checkout / installed
    # StaMPS tree (standard dev/CI without the nightly-e2e harness).
    phase_env = os.environ.get("PHASE_ROOT")
    stamps_env = os.environ.get("STAMPS")
    if not phase_env or not stamps_env:
        pytest.skip("PHASE_ROOT and STAMPS env vars required; nightly-e2e CI job sets these")
    phase_root = Path(phase_env)
    stamps_root = Path(stamps_env)
    fixture = stamps_root / "tests/fixtures/synthetic_ps_small"
    if not fixture.exists():
        pytest.skip(f"Fixture not built yet: {fixture}")

    # Stage data dir as PHASE expects (one folder per acquisition date)
    data_dir = tmp_path / "data"
    shutil.copytree(fixture, data_dir)

    # Compose a MATLAB driver that calls PHASE's command-builder.
    # PHASE_StaMPS.mlapp delegates to MatlabFunctions/run_stamps.m, which
    # builds the mt_prep_snap argv and shells out via system(). Calling
    # run_stamps directly bypasses the AppDesigner UI but exercises the
    # exact command-composition path that ships in v1.0.0.
    script = tmp_path / "drive.m"
    script.write_text(
        f"addpath('{phase_root.as_posix()}/MatlabFunctions');\n"
        f"cd('{data_dir.as_posix()}');\n"
        # Args mirror PHASE_StaMPS.mlapp's "Run StaMPS" defaults:
        #   master_date, data_dir, da_thresh, rg_patches, az_patches,
        #   rg_overlap, az_overlap.
        f"run_stamps('20200101', '{data_dir.as_posix()}', 0.4, 1, 1, 50, 50);\n"
        f"exit(0);\n",
        encoding="utf-8",
    )

    # MATLAB returns 0 on a clean exit; integration failure manifests as
    # nonzero RC OR missing output artifacts (checked below).
    proc = subprocess.run(
        ["matlab", "-batch", f"run('{script.as_posix()}')"],
        cwd=data_dir,
        capture_output=True,
        timeout=600,
    )
    stderr = proc.stderr.decode(errors="replace")
    assert proc.returncode == 0, f"MATLAB exited {proc.returncode}: {stderr}"

    # Concrete artifact assertions — these prove the PHASE→shim→Python→MATLAB
    # chain ran end-to-end, not just that MATLAB returned 0.
    assert (data_dir / "processor.txt").read_bytes() == b"snap\n", (
        "processor.txt missing or wrong — PHASE did not invoke " "mt_prep_snap.bat correctly"
    )
    assert (
        data_dir / "patch.list"
    ).exists(), "patch.list missing — Python port did not write split-into-patches output"
    assert (
        data_dir / "PATCH_1"
    ).is_dir(), "PATCH_1 dir missing — selpsc_patch / split-the-stack stage did not run"
