"""Byte-identity test: the Python mt_prep_snap port produces output
that matches the committed linux+csh golden tree under
tests/golden/linux_csh/ps_single/.

Text + integer artifacts must be byte-identical (algorithmic identity
with the csh pipeline); float32 binaries (.flt, .da, .hgt, .ph, .ll)
are compared ulp-tolerant via tests/golden/_verify.py — last-bit drift
between glibc versions on the committed-golden host and the test host
is expected. Full byte-identity under MinGW is exercised by AC3;
MSVC ulp-tolerance by AC4.

Task 2c.3 in the port plan.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "golden"))
import _verify  # noqa: E402  — local helper, not a package


@pytest.mark.linux_only
def test_python_mt_prep_snap_matches_csh_golden(stamps_root: Path, tmp_path: Path):
    golden = stamps_root / "tests/golden/linux_csh/ps_single"
    if not golden.exists():
        pytest.skip(
            f"golden tree not yet captured ({golden} missing). Run: bash tests/golden/capture.sh"
        )
    fixture = stamps_root / "tests/fixtures/synthetic_ps"
    if not (fixture / "rslc/20200101.rslc").exists():
        pytest.skip(f"fixture {fixture} not generated — run tests/fixtures/generate_fixtures.py")

    # Build the C++ binaries if missing. Skip silently under MinGW CI where
    # tooling differs — that job runs a separate byte-identity check.
    if not (stamps_root / "bin/calamp").exists():
        cmake = shutil.which("cmake")
        if cmake is None:
            pytest.skip("cmake not on PATH — cannot build C++ binaries")
        subprocess.run(
            [
                cmake,
                "-S",
                str(stamps_root / "src"),
                "-B",
                str(stamps_root / "build"),
                "-DCMAKE_BUILD_TYPE=Release",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [cmake, "--build", str(stamps_root / "build"), "--parallel"],
            check=True,
            capture_output=True,
        )

    # Match the canonical fixture path capture.sh uses, so .in files
    # produced by the Python port byte-match the committed golden.
    canonical = Path("/tmp/stamps_golden_fixture/ps_single")
    canonical.parent.mkdir(parents=True, exist_ok=True)
    if canonical.is_symlink() or canonical.exists():
        canonical.unlink() if canonical.is_symlink() else shutil.rmtree(canonical)
    canonical.symlink_to(fixture)

    workdir = tmp_path / "run"
    workdir.mkdir()

    env = {
        **os.environ,
        "STAMPS": str(stamps_root),
        "PATH": f"{stamps_root}/bin{os.pathsep}{os.environ.get('PATH', '')}",
        "LC_ALL": "C",
        "PYTHONUNBUFFERED": "1",
    }
    matlab_shim = workdir / "matlab"
    matlab_shim.write_text("#!/bin/sh\ncat >/dev/null; exit 0\n")
    matlab_shim.chmod(0o755)
    env["PATH"] = f"{workdir}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "stamps.mt_prep_snap",
            "20200101",
            str(canonical),
            "0.4",
            "1",
            "1",
            "50",
            "50",
        ],
        cwd=workdir,
        env=env,
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0, (
        f"mt_prep_snap failed:\nstdout:\n{result.stdout.decode(errors='replace')}\n"
        f"stderr:\n{result.stderr.decode(errors='replace')}"
    )

    # Run the fresh workdir tree through the same classifier the CI
    # verify step uses: byte-identical for text/int, ulp-tolerant for
    # float32. The Python port's run-local shim (matlab) and logs are
    # not in the golden tree so they're naturally ignored.
    mismatches = _verify.compare_trees(
        golden,
        workdir,
        ignore_extras={"matlab", "fixture", "ps_parms_initial.log", "sb_parms_initial.log"},
    )
    assert not mismatches, (
        "Python port output diverged from csh golden (see _verify classification):\n  "
        + "\n  ".join(mismatches)
    )
