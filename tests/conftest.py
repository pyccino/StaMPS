"""Global pytest fixtures for StaMPS tests."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

STAMPS_ROOT = Path(__file__).parent.parent.resolve()


# Register a global Hypothesis profile at module load so every property test
# in the suite inherits the same reproducibility settings (max_examples,
# deadline, health-check suppressions) without per-test `@settings` overrides.
# Windows CI is slow enough that Hypothesis's default deadline triggers
# spurious flakes; disabling it here centralises the decision.
try:
    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "default",
        max_examples=100,
        deadline=None,  # Windows CI is slow; avoid flaky deadline failures
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    settings.load_profile("default")
except ImportError:
    pass


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip tests marked linux_only / windows_only / requires_tcsh /
    requires_matlab / windows_mingw based on the host. Keeps the marker-aware
    tests implicit (no per-test skipif boilerplate) and matches the PHASE-side
    conftest.

    Also widens the default 120s per-test timeout (see `addopts` in
    pyproject.toml) to 900s for tests marked `nightly`; those shell out to
    MATLAB / full pipeline runs with 300-600s subprocess budgets of their own.
    The tight default exists to bound Hypothesis property tests whose
    deadline=None was set to dodge Windows-CI flakes — so the hard
    pytest-timeout is now the only runaway-loop safeguard.
    """
    skip_non_linux = pytest.mark.skip(reason="test marked linux_only; host is not Linux")
    skip_non_windows = pytest.mark.skip(reason="test marked windows_only; host is not Windows")
    skip_no_tcsh = pytest.mark.skip(reason="test marked requires_tcsh; tcsh not on PATH")
    is_linux = sys.platform.startswith("linux")
    is_windows = sys.platform.startswith("win")
    have_tcsh = shutil.which("tcsh") is not None
    have_matlab = shutil.which("matlab") is not None or shutil.which("matlab.exe") is not None
    is_windows_mingw = sys.platform.startswith("win") and (
        shutil.which("gcc") is not None or shutil.which("mingw32-make") is not None
    )
    for item in items:
        if "linux_only" in item.keywords and not is_linux:
            item.add_marker(skip_non_linux)
        if "windows_only" in item.keywords and not is_windows:
            item.add_marker(skip_non_windows)
        if "requires_tcsh" in item.keywords and not have_tcsh:
            item.add_marker(skip_no_tcsh)
        if "requires_matlab" in item.keywords and not have_matlab:
            item.add_marker(pytest.mark.skip(reason="requires_matlab: matlab not on PATH"))
        if "windows_mingw" in item.keywords and not is_windows_mingw:
            item.add_marker(pytest.mark.skip(reason="windows_mingw: requires Windows + MinGW"))
        if "nightly" in item.keywords:
            item.add_marker(pytest.mark.timeout(900))


@pytest.fixture(scope="session")
def stamps_root() -> Path:
    return STAMPS_ROOT


@pytest.fixture(scope="session")
def bin_dir(stamps_root: Path) -> Path:
    return stamps_root / "bin"


@pytest.fixture(scope="session")
def has_tcsh() -> bool:
    return shutil.which("tcsh") is not None


@pytest.fixture
def tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _default_c_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to C locale. Individual tests may override by
    calling monkeypatch.setenv themselves (LIFO teardown restores this)."""
    for var in ("LC_ALL", "LC_NUMERIC", "LC_COLLATE", "LC_TIME"):
        monkeypatch.setenv(var, "C")


@pytest.fixture(scope="session")
def phase_root() -> Path:
    """Root of a PHASE checkout, supplied by env var PHASE_ROOT.

    Phase 5/6 tests (PHASE-side .m edits, .mlapp regenerator, AC7 launch
    test, nightly E2E) require a PHASE working copy alongside StaMPS.
    Skip the test cleanly when not configured rather than ERROR at
    collection time.
    """
    raw = os.environ.get("PHASE_ROOT")
    if not raw:
        pytest.skip("PHASE_ROOT env var not set; PHASE-side test skipped")
    p = Path(raw).resolve()
    if not p.is_dir():
        pytest.skip(f"PHASE_ROOT={raw!r} is not a directory; test skipped")
    return p
