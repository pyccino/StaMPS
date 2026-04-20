"""Acceptance test: if this passes on a fresh Win11 with MATLAB R2023a+ + Python 3.11 +
SNAP 9.x, v1.0.0 ships.

Run manually:  pytest tests/test_acceptance.py -v -s
"""

import os
import subprocess
from pathlib import Path

import pytest

STAMPS = Path(os.environ["STAMPS"])


@pytest.mark.windows_only
def test_ac1_install_windows_ps1_can_download(tmp_path):
    """AC1: install-windows.ps1 runs clean through download + verify + unpack."""
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(STAMPS / "install-windows.ps1"),
            "-InstallDir",
            str(tmp_path),
            "-DryRun",
        ],
        capture_output=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")


@pytest.mark.windows_only
@pytest.mark.requires_matlab
def test_ac2_mt_prep_snap_bat_runs_to_completion(tmp_path):
    """AC1 end-to-end: .bat shim launches Python, which launches MATLAB, which
    completes ps_parms_initial."""
    # Copy synthetic fixture
    import shutil

    shutil.copytree(STAMPS / "tests/fixtures/synthetic_ps", tmp_path / "data")
    proc = subprocess.run(
        [str(STAMPS / "bin/mt_prep_snap.bat"), "20200101", str(tmp_path / "data"), "0.4"],
        cwd=tmp_path,
        capture_output=True,
        timeout=300,
    )
    assert proc.returncode == 0


@pytest.mark.windows_only
def test_ac3_windows_mingw_byte_identity_against_linux_golden():
    """AC3: Windows-MinGW output byte-matches Linux golden.

    Requires evidence at tests/runs/windows_mingw_ps_single/ — produced by
    the build-windows-mingw CI job (Task 1.9) running the synthetic_ps
    fixture and uploading artifacts. Test FAILS (not skips) if absent so
    AC3 is never silently bypassed.
    """
    import hashlib

    linux_golden = STAMPS / "tests/golden/linux_csh/ps_single"
    windows_out = STAMPS / "tests/runs/windows_mingw_ps_single"
    assert windows_out.exists(), (
        f"AC3 evidence missing: {windows_out} not present. "
        "Download build-windows-mingw artifact from CI before running."
    )
    for golden in linux_golden.rglob("*"):
        if not golden.is_file():
            continue
        rel = golden.relative_to(linux_golden)
        actual = windows_out / rel
        assert actual.exists(), f"Missing: {rel}"
        assert (
            hashlib.sha256(golden.read_bytes()).hexdigest()
            == hashlib.sha256(actual.read_bytes()).hexdigest()
        ), f"Byte-identity violated: {rel}"


# Files that AC4 treats as text (must byte-match) vs. binary (ulp-tolerant).
_AC4_TEXT_SUFFIXES = {".txt", ".out", ".log", ".list", ".par", ".in"}


def _ulp_compare_binary(
    a_bytes: bytes, b_bytes: bytes, rtol: float = 1e-6, atol: float = 0.0
) -> bool:
    """Compare two raw float32/complex64 binary buffers within tolerance.

    StaMPS C++ binaries write little-endian float32 (or pairs for complex).
    We treat the buffers as float32 arrays and compare element-wise.
    """
    import struct

    if len(a_bytes) != len(b_bytes):
        return False
    if len(a_bytes) % 4 != 0:
        return a_bytes == b_bytes  # not float32-aligned; require exact
    n = len(a_bytes) // 4
    a = struct.unpack(f"<{n}f", a_bytes)
    b = struct.unpack(f"<{n}f", b_bytes)
    for x, y in zip(a, b, strict=False):
        # NaN-safe: matching NaNs are considered equal
        if x != x and y != y:
            continue
        diff = abs(x - y)
        if diff > atol + rtol * abs(y):
            return False
    return True


@pytest.mark.windows_only
def test_ac4_windows_msvc_text_byte_identity_binary_ulp_tolerant():
    """AC4: Windows-MSVC text byte-matches; binary outputs match within
    rtol=1e-6, atol=0.

    Requires evidence at tests/runs/windows_msvc_ps_single/ — produced by
    the build-windows-msvc CI job uploading artifacts. FAIL (not skip) if
    absent.
    """
    import hashlib

    linux_golden = STAMPS / "tests/golden/linux_csh/ps_single"
    windows_out = STAMPS / "tests/runs/windows_msvc_ps_single"
    assert windows_out.exists(), (
        f"AC4 evidence missing: {windows_out} not present. "
        "Download build-windows-msvc artifact from CI before running."
    )
    text_violations = []
    binary_violations = []
    for golden in linux_golden.rglob("*"):
        if not golden.is_file():
            continue
        rel = golden.relative_to(linux_golden)
        actual = windows_out / rel
        assert actual.exists(), f"Missing: {rel}"
        if golden.suffix.lower() in _AC4_TEXT_SUFFIXES:
            if (
                hashlib.sha256(golden.read_bytes()).hexdigest()
                != hashlib.sha256(actual.read_bytes()).hexdigest()
            ):
                text_violations.append(str(rel))
        else:
            if not _ulp_compare_binary(
                golden.read_bytes(), actual.read_bytes(), rtol=1e-6, atol=0.0
            ):
                binary_violations.append(str(rel))
    assert not text_violations, f"AC4 text byte-identity failures: {text_violations}"
    assert not binary_violations, f"AC4 binary ulp-tolerance failures: {binary_violations}"


@pytest.mark.windows_only
def test_ac5_all_7_binaries_built_on_windows():
    """AC5: seven C++ binaries build from CMake on Windows."""
    for name in (
        "calamp",
        "cpxsum",
        "pscphase",
        "pscdem",
        "psclonlat",
        "selpsc_patch",
        "selsbc_patch",
    ):
        exe = STAMPS / "bin" / f"{name}.exe"
        assert exe.exists(), f"{exe} not built"


def test_ac6_ci_green_on_main():
    """AC6: latest commit on windows-port/main has all-green CI.

    `gh api` uses `{owner}/{repo}` placeholder syntax — NOT `:owner/:repo`
    (which is the old REST-template syntax that gh does not interpolate).
    """
    import json

    proc = subprocess.run(
        ["gh", "api", "repos/{owner}/{repo}/commits/windows-port%2Fmain/status"],
        capture_output=True,
        timeout=30,
        cwd=STAMPS,
    )
    if proc.returncode != 0:
        pytest.skip(f"gh CLI failed (not configured?): {proc.stderr.decode(errors='replace')}")
    data = json.loads(proc.stdout)
    failed = [s for s in data.get("statuses", []) if s["state"] != "success"]
    assert not failed, f"Failing checks: {[s['context'] for s in failed]}"


@pytest.mark.windows_only
@pytest.mark.requires_matlab
def test_ac7_phase_stamps_mlapp_launches_on_windows(phase_root: Path):
    """AC7: PHASE_StaMPS.mlapp loads on Windows without error."""
    proc = subprocess.run(
        [
            "matlab",
            "-batch",
            f"cd('{phase_root}/PHASE_Preprocessing'); "
            f"appdesigner.internal.serialization.app.readMLAPPFile("
            f"'PHASE_StaMPS.mlapp'); exit(0);",
        ],
        capture_output=True,
        timeout=180,
    )
    assert proc.returncode == 0
