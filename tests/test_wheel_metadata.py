"""Wheel build smoke: verify pyproject metadata produces a sensible wheel."""

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _project_table() -> dict:
    """Parse `[project]` table from the repo's pyproject.toml."""
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]


def test_wheel_builds_in_temp_dir(tmp_path: Path) -> None:
    """python -m build produces .whl + .tar.gz from current source tree.

    Skips when the `build` package isn't available — some CI jobs
    (build-linux, build-macos pytest steps) install `.[test]` but not
    `build`, which ships via `[build-system].requires` only. The
    dedicated `wheel-build-smoke` job installs `build` explicitly.
    """
    # find_spec("build") alone gives a false positive: CMake creates a
    # `build/` directory which PEP 420 treats as a namespace package
    # without the real `build` PyPI package being installed. Verify the
    # runnable CLI entry point `build.__main__` exists — that's what
    # `python -m build` actually executes.
    if importlib.util.find_spec("build.__main__") is None:
        pytest.skip("'build' PyPI package not installed (dedicated wheel CI job handles this)")
    repo_root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(tmp_path)],
        cwd=repo_root,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    wheels = list(tmp_path.glob("*.whl"))
    sdists = list(tmp_path.glob("*.tar.gz"))
    assert wheels, "no wheel produced"
    assert sdists, "no sdist produced"


def test_license_declared() -> None:
    """GPL-3.0-or-later must be recorded so the published wheel carries it."""
    project = _project_table()
    license_field = project["license"]
    # PEP 621 / setuptools accepts either {text = "..."} table form or a
    # bare string (SPDX); match whichever surface we ship.
    if isinstance(license_field, dict):
        assert license_field.get("text") == "GPL-3.0-or-later"
    else:
        assert license_field == "GPL-3.0-or-later"


def test_maintainers_non_empty() -> None:
    """At least one maintainer entry so PyPI shows a contact row."""
    project = _project_table()
    maintainers = project.get("maintainers", [])
    assert maintainers, "[project].maintainers must not be empty"
    # Each entry should have at least a `name` (email is optional per PEP 621).
    assert all("name" in m for m in maintainers)


def test_readme_points_at_README_md() -> None:
    """PyPI renders `readme` as the long description; point it at the main README."""
    project = _project_table()
    assert project.get("readme") == "README.md"


def test_urls_point_at_pyccino_fork() -> None:
    """At least one project URL must point at the pyccino/StaMPS fork."""
    project = _project_table()
    urls = project.get("urls", {})
    assert urls, "[project.urls] must not be empty"
    assert any(
        "pyccino/StaMPS" in url for url in urls.values()
    ), f"no URL references pyccino/StaMPS fork: {urls!r}"
