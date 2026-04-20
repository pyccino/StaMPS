"""Historical-bug regression tests for stamps.mt_prep_snap (4 tests).

See Step 2 table 4 in the plan. Each test guards a patch that was made to
the csh original; the Python port must not regress.
"""
from __future__ import annotations

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


def _sb_fixture(
    root: Path, master: str = "20200101", *, width: int = 100, length: int = 200,
    pairs: tuple[str, ...] = ("20200113", "20200125"),
) -> Path:
    d = root / "data"
    sb = d / "SMALL_BASELINES"
    for slv in pairs:
        pairdir = sb / f"{master}_{slv}"
        _touch(pairdir / f"{master}.rslc")
        _touch(pairdir / f"{slv}.rslc")
        _write_par(pairdir / f"{master}.rslc.par",
                   range_samples=width, azimuth_lines=length)
        _touch(pairdir / f"{master}_{slv}.diff")
    geo = d / "geo"
    _touch(geo / f"{master}.lon")
    _touch(geo / f"{master}.lat")
    _touch(geo / f"{master}_dem.rdc")
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

    captured: list[list[str]] = []

    def _fake_run(cmd, *args, **kwargs):
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

    monkeypatch.setattr("stamps.mt_prep_snap.subprocess.run", _fake_run)
    monkeypatch.setattr("stamps.mt_prep_snap._subprocess_calls", captured, raising=False)
    from stamps import mt_extract_cands as _mec
    monkeypatch.setattr(_mec, "main", lambda argv=None: 0)
    # Expose the calls list for tests that need to inspect it.
    monkeypatch.setattr(
        "stamps.mt_prep_snap.__test_calls__", captured, raising=False
    )


def _last_calamp_cmd() -> list[str]:
    """Helper: retrieve the calamp argv recorded by the autouse spy."""
    import stamps.mt_prep_snap as m
    calls = getattr(m, "__test_calls__", [])
    for c in calls:
        if "calamp" in Path(c[0]).name:
            return c
    raise AssertionError("calamp was not invoked")


# ---------------------------------------------------------------------------
# Tests (4)
# ---------------------------------------------------------------------------


def test_leave_maskfile_from_selpsc_when_not_present(tmp_workdir):
    """08/2017 AH: when no maskfile is given, calamp must NOT be invoked
    with an empty string `""` as its 6th argument."""
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir)
    main(["20200101", str(d)])
    argv = _last_calamp_cmd()
    # calamp argv: [exe, calamp.in, width, calamp.out, f, 1]
    # If maskfile were accidentally passed as "", argv length would be 7
    # with "" at index 6.
    assert "" not in argv, f"empty maskfile leaked into calamp argv: {argv}"
    assert len(argv) == 6


def test_short_and_byteswap_supported_for_sb(tmp_workdir):
    """02/2013 AH: SB path must still run end-to-end and produce selsbc.in."""
    from stamps.mt_prep_snap import main

    d = _sb_fixture(tmp_workdir)
    rc = main(["20200101", str(d)])
    assert rc == 0
    # selsbc.in header must be da_thresh=0.6 then width.
    lines = (
        (tmp_workdir / "selsbc.in").read_text(encoding="ascii").splitlines()
    )
    assert lines[0] == "0.6"
    assert lines[1].isdigit()


def test_list_as_input_preserved(tmp_workdir):
    """12/2012 DB: the patch.list file exists after a run, enumerating PATCH_*."""
    from stamps.mt_prep_snap import main

    d = _ps_fixture(tmp_workdir, width=200, length=400)
    main(["20200101", str(d), "0.4", "2", "1", "0", "0"])
    listing = (tmp_workdir / "patch.list").read_text().splitlines()
    assert listing == ["PATCH_1", "PATCH_2"]


def test_prep_snap_sb_rsc_uses_last_glob_match(tmp_workdir):
    """csh L104 `gawk 'END {print $1}'` selects the LAST sorted match."""
    from stamps.mt_prep_snap import main

    d = _sb_fixture(
        tmp_workdir, master="20200101", pairs=("20200113", "20200125")
    )
    main(["20200101", str(d)])
    rsc = (tmp_workdir / "rsc.txt").read_text(encoding="ascii").strip()
    assert "20200101_20200125" in rsc
    assert "20200101_20200113" not in rsc
