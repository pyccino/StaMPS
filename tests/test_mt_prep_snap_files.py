"""File-content tests for stamps.mt_prep_snap (12 tests).

Covers the rows in Task 2b.1 Step 2 table 2.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers (duplicated from test_mt_prep_snap_cli.py on purpose —
# keeps each test module self-contained).
# ---------------------------------------------------------------------------


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _write_par(
    path: Path, *, range_samples: int = 100, azimuth_lines: int = 200
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"range_samples: {range_samples}\nazimuth_lines: {azimuth_lines}\n",
        encoding="ascii",
    )
    return path


def _ps_fixture(
    root: Path,
    master: str = "20200101",
    *,
    width: int = 100,
    length: int = 200,
    extra_slcs: tuple[str, ...] = ("20200113",),
    extra_diffs: tuple[str, ...] = ("20200101_20200113", "20200101_20200125"),
) -> Path:
    d = root / "data"
    rslc = d / "rslc"
    _touch(rslc / f"{master}.rslc")
    _write_par(
        rslc / f"{master}.rslc.par", range_samples=width, azimuth_lines=length
    )
    for slv in extra_slcs:
        _touch(rslc / f"{slv}.rslc")
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
    diff0 = d / "diff0"
    for name in extra_diffs:
        _touch(diff0 / f"{name}.diff")
    return d


def _sb_fixture(
    root: Path,
    master: str = "20200101",
    *,
    width: int = 100,
    length: int = 200,
    pairs: tuple[str, ...] = ("20200113", "20200125"),
) -> Path:
    d = root / "data"
    sb = d / "SMALL_BASELINES"
    for i, slv in enumerate(pairs):
        pairdir = sb / f"{master}_{slv}"
        _touch(pairdir / f"{master}.rslc")
        _touch(pairdir / f"{slv}.rslc")
        _write_par(
            pairdir / f"{master}.rslc.par",
            range_samples=width,
            azimuth_lines=length,
        )
        _touch(pairdir / f"{master}_{slv}.diff")
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
    return d


# ---------------------------------------------------------------------------
# Autouse: same stubbing as the CLI tests.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stamps_env(monkeypatch: pytest.MonkeyPatch, tmp_path_factory) -> None:
    fake_stamps = tmp_path_factory.mktemp("stamps_root")
    (fake_stamps / "matlab").mkdir(parents=True, exist_ok=True)
    (fake_stamps / "matlab" / "ps_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "matlab" / "sb_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "bin").mkdir(parents=True, exist_ok=True)
    for b in ("calamp", "selpsc_patch", "selsbc_patch", "psclonlat", "pscdem", "pscphase"):
        (fake_stamps / "bin" / b).touch()
    monkeypatch.setenv("STAMPS", str(fake_stamps))

    from stamps import mt_prep_snap as _mod
    monkeypatch.setattr(_mod, "run_batch", lambda *a, **kw: 0)

    def _fake_run(cmd, *args, **kwargs):
        try:
            exe = Path(cmd[0]).name
        except Exception:
            exe = ""
        if "calamp" in exe and len(cmd) >= 4:
            try:
                Path(cmd[3]).write_bytes(b"")
            except Exception:
                pass
        r = MagicMock()
        r.returncode = 0
        return r

    monkeypatch.setattr("stamps.mt_prep_snap.subprocess.run", _fake_run)
    from stamps import mt_extract_cands as _mec
    monkeypatch.setattr(_mec, "main", lambda argv=None: 0)


# ---------------------------------------------------------------------------
# Tests (12)
# ---------------------------------------------------------------------------


def test_calamp_in_lists_sorted_slc_paths_ps(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, extra_slcs=("20200113", "20200125"))
    main(["20200101", str(d)])
    body = (tmp_workdir / "calamp.in").read_bytes().decode("ascii")
    lines = [ln for ln in body.split("\n") if ln]
    assert lines == sorted(lines)
    assert all(ln.endswith(".rslc") for ln in lines)


def test_calamp_in_lists_sb_slc_paths(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _sb_fixture(tmp_workdir)
    main(["20200101", str(d)])
    body = (tmp_workdir / "calamp.in").read_bytes().decode("ascii")
    lines = [ln for ln in body.split("\n") if ln]
    assert lines == sorted(lines)
    assert all("SMALL_BASELINES" in ln for ln in lines)


def test_selpsc_in_header_is_dathresh_then_width(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=256, length=512)
    main(["20200101", str(d), "0.4"])
    head = (tmp_workdir / "selpsc.in").read_text(encoding="ascii").splitlines()
    assert head[0] == "0.4"
    assert head[1] == "256"


def test_pscphase_in_header_then_diffs_ps(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(
        tmp_workdir,
        width=128,
        length=256,
        extra_diffs=("a_b", "c_d"),
    )
    main(["20200101", str(d)])
    lines = (
        (tmp_workdir / "pscphase.in").read_text(encoding="ascii").splitlines()
    )
    assert lines[0] == "128"
    diffs = lines[1:]
    assert all(ln.endswith(".diff") for ln in diffs)
    assert diffs == sorted(diffs)


def test_pscphase_in_uses_sb_diffs_when_sb(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _sb_fixture(tmp_workdir)
    main(["20200101", str(d)])
    lines = (
        (tmp_workdir / "pscphase.in").read_text(encoding="ascii").splitlines()
    )
    diffs = [ln for ln in lines[1:] if ln]
    assert diffs, "expected at least one SB diff path"
    assert all("SMALL_BASELINES" in ln for ln in diffs)


def test_pscdem_in_has_width_and_dem_rdc(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=512)
    main(["20200101", str(d)])
    lines = (
        (tmp_workdir / "pscdem.in").read_text(encoding="ascii").splitlines()
    )
    assert lines[0] == "512"
    # Exactly one dem.rdc line (may include trailing empty line).
    rdc_lines = [ln for ln in lines[1:] if ln.endswith("dem.rdc")]
    assert len(rdc_lines) == 1


def test_psclonlat_in_uses_head_1_not_end(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    # Add a second .lon / .lat sorted AFTER the master to prove head-1 is
    # used (first sorted — NOT last).
    (d / "geo" / "zzz.lon").touch()
    (d / "geo" / "zzz.lat").touch()
    main(["20200101", str(d)])
    lines = (
        (tmp_workdir / "psclonlat.in").read_text(encoding="ascii").splitlines()
    )
    assert len(lines) >= 3
    # First sorted .lon must be 20200101.lon, not zzz.lon.
    assert lines[1].endswith("20200101.lon")
    assert lines[2].endswith("20200101.lat")


def test_width_txt_is_integer_no_dot_zero(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=100)
    main(["20200101", str(d)])
    assert (tmp_workdir / "width.txt").read_bytes() == b"100\n"


def test_len_txt_is_integer_no_dot_zero(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, length=200)
    main(["20200101", str(d)])
    assert (tmp_workdir / "len.txt").read_bytes() == b"200\n"


def test_rsc_txt_points_to_resolved_par(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    content = (tmp_workdir / "rsc.txt").read_text(encoding="ascii").strip()
    # Must contain an absolute/resolvable path ending in .rslc.par
    assert content.endswith(".rslc.par")
    assert Path(content).exists()


def test_sb_rsc_is_last_sorted_not_first(tmp_workdir):
    """Regression: SB chooses the LAST sorted match (gawk END {}), PS first."""
    from stamps.mt_prep_snap import main

    # Build SB fixture with TWO par files for master — gawk END takes last.
    master = "20200101"
    d = _sb_fixture(tmp_workdir, master=master, pairs=("20200113", "20200125"))
    main([master, str(d)])
    rsc_line = (tmp_workdir / "rsc.txt").read_text(encoding="ascii").strip()
    # last sorted pair dir is 20200101_20200125
    assert "20200101_20200125" in rsc_line


@pytest.mark.skipif(
    sys.platform != "win32", reason="Windows-only LF guardrail"
)
def test_calamp_in_lf_on_windows(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    b = (tmp_workdir / "calamp.in").read_bytes()
    assert b"\r\n" not in b
