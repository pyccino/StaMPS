"""Smoke-test: `cmake -S external/snaphu -B <tmp>` + `cmake --build` produces
a working snaphu binary on POSIX (Linux/macOS) and MinGW.

Catches regressions in external/snaphu/CMakeLists.txt or future snaphu
version bumps where the source layout shifts. Skipped on MSVC (out of
scope: snaphu uses POSIX fork/getrusage).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.slow
def test_snaphu_builds_from_vendored_cmakelists(stamps_root: Path, tmp_path: Path):
    # snaphu cannot build under MSVC (POSIX fork/getrusage deps). On non-
    # Windows we attempt the build; on Windows we run only inside MSYS2
    # MINGW64 (detected via MSYSTEM) because the GitHub Actions MSVC runner
    # image happens to ship a random MinGW in its tool cache — so
    # `shutil.which("gcc")` is unreliable as a positive signal.
    if platform.system() == "Windows":
        if os.environ.get("MSYSTEM", "").upper() not in {"MINGW64", "MINGW32", "CLANG64"}:
            pytest.skip("Not in MSYS2 MinGW shell; snaphu build covered by MinGW CI job")
    if shutil.which("cmake") is None:
        pytest.skip("cmake not on PATH")
    if (
        shutil.which("make") is None
        and shutil.which("gmake") is None
        and shutil.which("mingw32-make") is None
    ):
        pytest.skip("GNU make required to build snaphu")

    build_dir = tmp_path / "build-snaphu"
    install_dir = tmp_path / "install-snaphu"

    configure = subprocess.run(
        [
            "cmake",
            "-S",
            str(stamps_root / "external/snaphu"),
            "-B",
            str(build_dir),
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        ],
        capture_output=True,
        timeout=120,
    )
    assert configure.returncode == 0, (
        f"cmake configure failed:\nstdout:\n{configure.stdout.decode(errors='replace')}\n"
        f"stderr:\n{configure.stderr.decode(errors='replace')}"
    )

    # Build downloads snaphu tarball, verifies SHA256, compiles via its own
    # Makefile, and installs into external/snaphu/bin/.
    build = subprocess.run(
        ["cmake", "--build", str(build_dir), "--parallel"],
        capture_output=True,
        timeout=600,  # first-time download + full compile
        env={**os.environ, "MAKEFLAGS": ""},  # avoid jobserver issues nested under pytest
    )
    assert build.returncode == 0, (
        f"snaphu build failed:\nstdout (tail):\n"
        f"{build.stdout.decode(errors='replace')[-4000:]}\nstderr (tail):\n"
        f"{build.stderr.decode(errors='replace')[-4000:]}"
    )

    # Binary is `snaphu` on POSIX, `snaphu.exe` on MinGW.
    snaphu_bin = stamps_root / "external/snaphu/bin/snaphu"
    if not snaphu_bin.exists():
        snaphu_bin = stamps_root / "external/snaphu/bin/snaphu.exe"
    assert snaphu_bin.exists(), f"snaphu binary not installed at {snaphu_bin}"
    assert snaphu_bin.stat().st_size > 50_000, "snaphu binary suspiciously small"

    # Running with no args should print usage and exit nonzero (standard
    # snaphu behavior). We only care that the binary isn't linked against
    # missing libs or crashes on invocation.
    result = subprocess.run([str(snaphu_bin)], capture_output=True, timeout=30)
    # snaphu prints to stderr when invoked without args; don't assert on rc
    output = (result.stdout + result.stderr).decode(errors="replace")
    assert (
        "snaphu" in output.lower()
    ), f"snaphu invocation produced no recognizable output:\n{output}"
