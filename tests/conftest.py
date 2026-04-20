"""Global pytest fixtures for StaMPS tests."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

STAMPS_ROOT = Path(__file__).parent.parent.resolve()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip tests marked linux_only / windows_only / requires_tcsh
    based on the host. Keeps the marker-aware tests implicit (no
    per-test skipif boilerplate) and matches the PHASE-side conftest.
    """
    skip_non_linux = pytest.mark.skip(reason="test marked linux_only; host is not Linux")
    skip_non_windows = pytest.mark.skip(reason="test marked windows_only; host is not Windows")
    skip_no_tcsh = pytest.mark.skip(reason="test marked requires_tcsh; tcsh not on PATH")
    is_linux = sys.platform.startswith("linux")
    is_windows = sys.platform.startswith("win")
    have_tcsh = shutil.which("tcsh") is not None
    for item in items:
        if "linux_only" in item.keywords and not is_linux:
            item.add_marker(skip_non_linux)
        if "windows_only" in item.keywords and not is_windows:
            item.add_marker(skip_non_windows)
        if "requires_tcsh" in item.keywords and not have_tcsh:
            item.add_marker(skip_no_tcsh)


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
def synthetic_ps_small_path() -> Path:
    """Build (on first request) and return ``tests/fixtures/synthetic_ps_small``.

    The 200x200 ``synthetic_ps`` tree is produced by test_generate_fixtures.py
    (session-scope-free, on-demand) and locked against a SHA256 manifest. The
    trimmed 20x20 ``_small`` variant is NOT committed (same rationale as the
    full-size one: generator is the source of truth, output is reproducible
    byte-for-byte from the seed) and is only needed by nightly-E2E +
    PHASE→StaMPS integration tests.

    Opt-in (not autouse) so unit-only pytest runs don't pay the build cost.
    Request this fixture explicitly from tests that need the small PS tree;
    the build is skipped if the directory already exists, so dev loop cost
    is zero after the first run.
    """
    from tests.fixtures.generate_fixtures import (
        SMALL_LENGTH,
        SMALL_WIDTH,
        generate_ps_fixture,
    )

    ps_small = STAMPS_ROOT / "tests" / "fixtures" / "synthetic_ps_small"
    if not ps_small.exists():
        generate_ps_fixture(ps_small, width=SMALL_WIDTH, length=SMALL_LENGTH)
    return ps_small


@pytest.fixture(scope="session")
def synthetic_sb_small_path() -> Path:
    """Build (on first request) and return ``tests/fixtures/synthetic_sb_small``.

    SB sibling of ``synthetic_ps_small_path`` — same opt-in semantics, same
    deterministic seed, same 20x20 raster geometry. Request explicitly from
    nightly-E2E / PHASE→StaMPS integration tests that exercise the SB path.
    """
    from tests.fixtures.generate_fixtures import (
        SMALL_LENGTH,
        SMALL_WIDTH,
        generate_sb_fixture,
    )

    sb_small = STAMPS_ROOT / "tests" / "fixtures" / "synthetic_sb_small"
    if not sb_small.exists():
        generate_sb_fixture(sb_small, width=SMALL_WIDTH, length=SMALL_LENGTH)
    return sb_small


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
