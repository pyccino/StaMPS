"""Patch-tiling tests for stamps.mt_prep_snap (6 tests).

Covers Step 2 table 3 in the plan.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


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
    d = root / "data"
    rslc = d / "rslc"
    _touch(rslc / f"{master}.rslc")
    _write_par(rslc / f"{master}.rslc.par", range_samples=width, azimuth_lines=length)
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
    diff0 = d / "diff0"
    _touch(diff0 / f"{master}_20200115.diff")
    return d


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
# Tests (6)
# ---------------------------------------------------------------------------


def test_patch_list_enumerates_in_range_major_order(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=1000, length=2000)
    main(["20200101", str(d), "0.4", "2", "2", "0", "0"])
    lines = [
        ln for ln in (tmp_workdir / "patch.list").read_text().splitlines() if ln
    ]
    # irg-major, iaz-minor:
    # irg=1,iaz=1 → PATCH_1 ; irg=1,iaz=2 → PATCH_2
    # irg=2,iaz=1 → PATCH_3 ; irg=2,iaz=2 → PATCH_4
    assert lines == ["PATCH_1", "PATCH_2", "PATCH_3", "PATCH_4"]


def test_patch_in_is_4_lines_lf(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=200, length=400)
    main(["20200101", str(d), "0.4", "2", "2", "5", "5"])
    for k in (1, 2, 3, 4):
        data = (tmp_workdir / f"PATCH_{k}" / "patch.in").read_bytes()
        assert b"\r\n" not in data
        non_empty = [ln for ln in data.decode("ascii").split("\n") if ln]
        assert len(non_empty) == 4


def test_patch_noover_in_is_4_lines_lf(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=200, length=400)
    main(["20200101", str(d), "0.4", "2", "2", "5", "5"])
    for k in (1, 2, 3, 4):
        data = (tmp_workdir / f"PATCH_{k}" / "patch_noover.in").read_bytes()
        assert b"\r\n" not in data
        non_empty = [ln for ln in data.decode("ascii").split("\n") if ln]
        assert len(non_empty) == 4


def test_stale_patch_dirs_removed_before_rerun(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=200, length=400)
    # Pre-seed a stale PATCH_99 dir in the work dir.
    stale = tmp_workdir / "PATCH_99"
    stale.mkdir()
    (stale / "junk.txt").write_text("junk")

    main(["20200101", str(d), "0.4", "1", "1", "0", "0"])
    assert not stale.exists(), "stale PATCH_99 should have been removed"
    assert (tmp_workdir / "PATCH_1").is_dir()


def test_stale_patch_list_removed_before_rerun(tmp_workdir):
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=200, length=400)
    stale_list = tmp_workdir / "patch.list"
    stale_list.write_text("PATCH_42\nPATCH_43\n")

    main(["20200101", str(d), "0.4", "1", "1", "0", "0"])
    new_lines = stale_list.read_text().splitlines()
    assert "PATCH_42" not in new_lines
    assert new_lines == ["PATCH_1"]


def test_iaz_resets_between_irg_iterations(tmp_workdir):
    """High-probability porting bug: iaz must reset per irg iteration."""
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=1000, length=2000)
    main(["20200101", str(d), "0.4", "2", "2", "0", "0"])
    # width_p=500 length_p=1000 overlap=0.
    # Correct PATCH_3 (irg=2, iaz=1): start_rg1=501, end_rg1=1000, start_az1=1
    p3 = (tmp_workdir / "PATCH_3" / "patch.in").read_text().splitlines()
    assert p3 == ["501", "1000", "1", "1000"], (
        f"iaz was not reset before irg=2; got {p3}"
    )
    p4 = (tmp_workdir / "PATCH_4" / "patch.in").read_text().splitlines()
    assert p4 == ["501", "1000", "1001", "2000"]
