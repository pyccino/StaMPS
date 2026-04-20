"""Verify CMakeLists.txt builds all 7 core binaries on every platform."""

import os
import subprocess
from pathlib import Path

import pytest

CORE_BINARIES = [
    "calamp",
    "cpxsum",
    "pscphase",
    "pscdem",
    "psclonlat",
    "selpsc_patch",
    "selsbc_patch",
]


@pytest.fixture(scope="module")
def cmake_build(stamps_root: Path, tmp_path_factory):
    build_dir = tmp_path_factory.mktemp("cmake_build")
    subprocess.check_call(
        [
            "cmake",
            "-S",
            str(stamps_root / "src"),
            "-B",
            str(build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
        ]
    )
    subprocess.check_call(["cmake", "--build", str(build_dir), "--config", "Release"])
    return build_dir


@pytest.mark.parametrize("name", CORE_BINARIES)
def test_cmake_builds_binary(name: str, cmake_build: Path, stamps_root: Path):
    exe_name = f"{name}.exe" if os.name == "nt" else name
    candidate = stamps_root / "bin" / exe_name
    assert candidate.exists(), f"{candidate} not produced by cmake build"


def test_ctest_smoke(cmake_build: Path):
    proc = subprocess.run(
        ["ctest", "--test-dir", str(cmake_build), "--output-on-failure", "-C", "Release"],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout.decode() + proc.stderr.decode()
