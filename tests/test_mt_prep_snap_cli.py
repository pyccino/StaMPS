"""CLI / argv tests for stamps.mt_prep_snap (18 tests).

All rows from Task 2b.1 Step 2 table 1 in the plan. Drives assertions
against the csh source lines referenced in each row.

Fixtures are built inline against `tmp_workdir` because the shared
`generate_fixtures.py` is not produced until Task 2c.1.
"""
from __future__ import annotations

import locale
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Synthetic-fixture helpers (lightweight; real rasters come from Task 2c.1).
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
    root: Path, master: str = "20200101", *, width: int = 100, length: int = 200
) -> Path:
    """Build a minimal PS-mode datadir: rslc/{master}.rslc[.par], geo/*.lon/lat/dem.rdc, diff0/*.diff."""
    d = root / "data"
    rslc = d / "rslc"
    _touch(rslc / f"{master}.rslc")
    _write_par(
        rslc / f"{master}.rslc.par", range_samples=width, azimuth_lines=length
    )
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
    diff0 = d / "diff0"
    _touch(diff0 / f"{master}_20200115.diff")
    return d


def _sb_fixture(
    root: Path, master: str = "20200101", *, width: int = 100, length: int = 200
) -> Path:
    """Build a minimal SB-mode datadir with SMALL_BASELINES layout."""
    d = root / "data"
    sb = d / "SMALL_BASELINES"
    pair = sb / f"{master}_20200115"
    _touch(pair / f"{master}.rslc")
    _write_par(
        pair / f"{master}.rslc.par", range_samples=width, azimuth_lines=length
    )
    _touch(pair / "20200115.rslc")
    _touch(pair / f"{master}_20200115.diff")
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
    return d


# ---------------------------------------------------------------------------
# Autouse patches: stub MATLAB + external binaries and resolve_bin globally.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stamps_env(monkeypatch: pytest.MonkeyPatch, tmp_path_factory) -> None:
    """Set STAMPS to a dummy path and stub run_batch + resolve_bin + subprocess.run."""
    fake_stamps = tmp_path_factory.mktemp("stamps_root")
    (fake_stamps / "matlab").mkdir(parents=True, exist_ok=True)
    (fake_stamps / "matlab" / "ps_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "matlab" / "sb_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "bin").mkdir(parents=True, exist_ok=True)
    # Create placeholder files for resolve_bin to find.
    for b in ("calamp", "selpsc_patch", "selsbc_patch", "psclonlat", "pscdem", "pscphase"):
        (fake_stamps / "bin" / b).touch()
    monkeypatch.setenv("STAMPS", str(fake_stamps))

    # Stub run_batch (MATLAB) to no-op.
    from stamps import mt_prep_snap as _mod

    monkeypatch.setattr(_mod, "run_batch", lambda *a, **kw: 0)

    # Stub subprocess.run so calamp / mt_extract_cands subprocesses don't run.
    # Create an empty calamp.out when calamp is "invoked" so the selfile
    # append step has something to attach.
    calls: list[list[str]] = []

    def _fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        # If calamp-looking call, produce a calamp.out so selfile append works.
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
        r.stdout = b""
        r.stderr = b""
        return r

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr("stamps.mt_prep_snap.subprocess.run", _fake_run)
    # Also stub mt_extract_cands.main so it doesn't run binaries.
    from stamps import mt_extract_cands as _mec

    monkeypatch.setattr(_mec, "main", lambda argv=None: 0)


# ---------------------------------------------------------------------------
# Tests (18)
# ---------------------------------------------------------------------------


def test_too_few_args_exits_4(tmp_workdir):
    from stamps.mt_prep_snap import main

    with pytest.raises(SystemExit) as ei:
        main(["20200101"])
    assert ei.value.code == 4


def test_usage_banner_matches_csh_verbatim(tmp_workdir, capsys):
    from stamps.mt_prep_snap import main, USAGE

    with pytest.raises(SystemExit):
        main([])
    err = capsys.readouterr().err
    # Preserves the L51 trailing-space on the az_overlap default line.
    assert "az_overlap (default 50) =" in USAGE
    assert USAGE in err


def test_detects_sb_when_small_baselines_exists(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _sb_fixture(tmp_workdir)
    main(["20200101", str(d)])
    assert (tmp_workdir / "selsbc.in").exists()
    assert not (tmp_workdir / "selpsc.in").exists()


def test_detects_ps_when_small_baselines_absent(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    assert (tmp_workdir / "selpsc.in").exists()
    assert not (tmp_workdir / "selsbc.in").exists()


def test_default_da_thresh_ps_is_0_4(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    first_line = (
        (tmp_workdir / "selpsc.in").read_text(encoding="ascii").splitlines()[0]
    )
    assert first_line == "0.4"


def test_default_da_thresh_sb_is_0_6(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _sb_fixture(tmp_workdir)
    main(["20200101", str(d)])
    first_line = (
        (tmp_workdir / "selsbc.in").read_text(encoding="ascii").splitlines()[0]
    )
    assert first_line == "0.6"


def test_explicit_da_thresh_overrides_default(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d), "0.35"])
    content = (tmp_workdir / "selpsc.in").read_text(encoding="ascii")
    assert content.splitlines()[0] == "0.35"


def test_da_thresh_preserves_decimal_dot_in_comma_locale(
    tmp_workdir, monkeypatch
):
    from stamps.mt_prep_snap import main

    # Attempt Italian locale; if unavailable, just ensure the Python port
    # treats da_thresh as opaque string, not locale-parsed.
    try:
        locale.setlocale(locale.LC_NUMERIC, "it_IT.UTF-8")
    except locale.Error:
        pass
    try:
        d = _ps_fixture(tmp_workdir)
        main(["20200101", str(d), "0.35"])
        content = (tmp_workdir / "selpsc.in").read_text(encoding="ascii")
        assert "0.35" in content
        assert "0,35" not in content
    finally:
        locale.setlocale(locale.LC_NUMERIC, "C")


def test_single_patch_boundary_math(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=100, length=200)
    # prg=1 paz=1 overlap=50,50
    main(["20200101", str(d), "0.4", "1", "1", "50", "50"])
    patch = (tmp_workdir / "PATCH_1" / "patch.in").read_text(encoding="ascii")
    assert patch.splitlines() == ["1", "100", "1", "200"]


def test_multiple_patches_boundary_math(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=1000, length=2000)
    main(["20200101", str(d), "0.4", "2", "2", "10", "10"])
    # 4 patches enumerated PATCH_1..PATCH_4 in irg-major / iaz-minor order.
    assert (tmp_workdir / "PATCH_1").is_dir()
    assert (tmp_workdir / "PATCH_4").is_dir()
    # width_p = 500, length_p = 1000, overlap=10
    p1 = (tmp_workdir / "PATCH_1" / "patch.in").read_text().splitlines()
    assert p1 == ["1", "510", "1", "1010"]
    p2 = (tmp_workdir / "PATCH_2" / "patch.in").read_text().splitlines()
    # irg=1,iaz=2 → start_az=1000-10+1? actually start_az1=1001, -10=991
    assert p2 == ["1", "510", "991", "2000"]
    p3 = (tmp_workdir / "PATCH_3" / "patch.in").read_text().splitlines()
    # irg=2,iaz=1 → start_rg1=501, start_rg=491, end_rg1=1000, end_rg=1000
    assert p3 == ["491", "1000", "1", "1010"]
    p4 = (tmp_workdir / "PATCH_4" / "patch.in").read_text().splitlines()
    assert p4 == ["491", "1000", "991", "2000"]


def test_patch_fits_exactly_no_overlap_clipping(tmp_workdir):
    """width % prg == 0 and overlap_rg=0 → last patch's end_rg == width."""
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=1000, length=500)
    main(["20200101", str(d), "0.4", "2", "1", "0", "0"])
    # PATCH_2 end_rg must equal width (line 2)
    lines = (tmp_workdir / "PATCH_2" / "patch.in").read_text().splitlines()
    assert lines[1] == "1000"


def test_patch_exceeds_width_clipped_at_edge(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=100, length=200)
    main(["20200101", str(d), "0.4", "1", "1", "50", "50"])
    # end_rg1 = 100, +overlap=150 > width=100 → clipped to 100
    lines = (tmp_workdir / "PATCH_1" / "patch.in").read_text().splitlines()
    assert int(lines[1]) == 100


def test_patch_start_below_one_clipped_at_edge(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=100, length=200)
    main(["20200101", str(d), "0.4", "1", "1", "50", "50"])
    # start_rg1=1 - overlap=50 → -49 → clipped to 1
    lines = (tmp_workdir / "PATCH_1" / "patch.in").read_text().splitlines()
    assert lines[0] == "1"


def test_integer_division_not_float(tmp_workdir):
    """width=101 / prg=2 → width_p=50 (truncate), NOT 50.5."""
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=101, length=200)
    main(["20200101", str(d), "0.4", "2", "1", "0", "0"])
    # width_p=50. PATCH_1 end_rg1=50, end_rg clipped to min(101, 50)=50.
    p1 = (tmp_workdir / "PATCH_1" / "patch.in").read_text().splitlines()
    assert p1[1] == "50"
    # PATCH_2 start_rg1=51, end_rg1=100 → end_rg clipped/capped to min(101,100)=100
    p2 = (tmp_workdir / "PATCH_2" / "patch.in").read_text().splitlines()
    assert p2[0] == "51"
    assert p2[1] == "100"


def test_processor_txt_is_literal_snap_newline(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    assert (tmp_workdir / "processor.txt").read_bytes() == b"snap\n"


def test_maskfile_missing_exits_2(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    nonexistent = tmp_workdir / "does_not_exist.mask"
    with pytest.raises(SystemExit) as ei:
        main(
            [
                "20200101",
                str(d),
                "0.4",
                "1",
                "1",
                "50",
                "50",
                str(nonexistent),
            ]
        )
    assert ei.value.code == 2


def test_maskfile_present_passed_through(tmp_workdir, monkeypatch):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    mask = tmp_workdir / "mask.char"
    mask.write_bytes(b"\x00" * 16)

    # Capture subprocess.run calls (override the autouse stub with a spy).
    captured: list[list[str]] = []

    def _spy(cmd, *a, **kw):
        captured.append(list(cmd))
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

    monkeypatch.setattr("stamps.mt_prep_snap.subprocess.run", _spy)
    # Capture mt_extract_cands argv too.
    mec_argv: list[list[str]] = []

    def _fake_mec_main(argv=None):
        mec_argv.append(list(argv or []))
        return 0

    monkeypatch.setattr("stamps.mt_extract_cands.main", _fake_mec_main)

    main(["20200101", str(d), "0.4", "1", "1", "50", "50", str(mask)])
    # calamp invocation must carry the maskfile path.
    calamp_calls = [c for c in captured if Path(c[0]).name.startswith("calamp")]
    assert calamp_calls, "calamp was not invoked"
    assert any(str(mask) in c for c in calamp_calls)
    # mt_extract_cands argv must also carry the mask.
    assert mec_argv, "mt_extract_cands.main was not invoked"
    assert str(mask) in mec_argv[0]


def test_no_lon_file_exits_3(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    # Remove the .lon file
    for p in (d / "geo").glob("*.lon"):
        p.unlink()
    with pytest.raises(SystemExit) as ei:
        main(["20200101", str(d)])
    assert ei.value.code == 3
