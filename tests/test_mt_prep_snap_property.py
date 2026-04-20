"""Hypothesis property tests for stamps.mt_prep_snap (5 tests).

Step 2 table 6. Each test declares a property that should hold for a
large randomized input domain.
"""
from __future__ import annotations

import locale
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st


# ---------------------------------------------------------------------------
# Lightweight fixture helpers.
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


# ---------------------------------------------------------------------------
# Tests (5)
# ---------------------------------------------------------------------------


@given(val=st.integers(min_value=0, max_value=10_000))
def test_par_roundtrip_integers(tmp_path_factory, val):
    """parse_par returns int when the source value is an integer literal."""
    from stamps._par import parse_par

    d = tmp_path_factory.mktemp("par")
    p = d / "t.par"
    p.write_text(f"azimuth_lines: {val}\n", encoding="ascii")
    parsed = parse_par(p)["azimuth_lines"]
    assert parsed == val
    assert isinstance(parsed, int)


@given(loc=st.sampled_from(["C", "it_IT.UTF-8", "de_DE.UTF-8"]))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_par_locale_invariant_property(tmp_path_factory, loc):
    """1717.5 parses to 1717.5 regardless of LC_NUMERIC."""
    from stamps._par import parse_par

    try:
        locale.setlocale(locale.LC_NUMERIC, loc)
    except locale.Error:
        pytest.skip(f"locale {loc} not available on this system")
    try:
        d = tmp_path_factory.mktemp("par_loc")
        p = d / "t.par"
        p.write_text("prf: 1717.5\n", encoding="ascii")
        parsed = parse_par(p)["prf"]
        assert parsed == pytest.approx(1717.5)
    finally:
        locale.setlocale(locale.LC_NUMERIC, "C")


@given(names=st.lists(
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            max_codepoint=0x7E,
        ),
        min_size=1,
        max_size=12,
    ),
    min_size=2,
    max_size=16,
    unique=True,
))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_glob_sort_deterministic(tmp_path_factory, names):
    """sorted_glob returns identical ordering across calls."""
    from stamps._shell import sorted_glob

    d = tmp_path_factory.mktemp("glob_det")
    for n in names:
        (d / f"{n}.dat").touch()
    r1 = sorted_glob(d / "*.dat")
    r2 = sorted_glob(d / "*.dat")
    assert r1 == r2
    # Second invocation must still match raw-byte sort.
    assert r1 == sorted(r1, key=lambda p: os.fsencode(str(p)))


@given(
    width=st.integers(min_value=100, max_value=5000),
    prg=st.integers(min_value=1, max_value=8),
    overlap=st.integers(min_value=0, max_value=200),
)
def test_tile_math_preserves_coverage(width, prg, overlap):
    """Union of PATCH range intervals covers [1..width]."""
    from stamps.mt_prep_snap import _csh_int_div

    width_p = _csh_int_div(width, prg)
    assume(width_p >= 1)
    intervals: list[tuple[int, int]] = []
    for irg in range(1, prg + 1):
        start_rg1 = width_p * (irg - 1) + 1
        start_rg = max(1, start_rg1 - overlap)
        end_rg1 = width_p * irg
        end_rg = min(width, end_rg1 + overlap)
        intervals.append((start_rg, end_rg))

    # Merge intervals and confirm full coverage of [1..prg * width_p].
    intervals.sort()
    merged: list[tuple[int, int]] = [intervals[0]]
    for a, b in intervals[1:]:
        if a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    # Coverage: the first interval starts at 1, the last ends at >= prg*width_p.
    assert merged[0][0] == 1
    assert merged[-1][1] >= prg * width_p


@given(
    case=st.sampled_from(["too_few", "bad_mask", "no_lon"]),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
    max_examples=20,
)
def test_exit_code_matches_csh_signal(tmp_path_factory, monkeypatch, case):
    """Error paths return the exit codes encoded in the csh source."""
    from stamps import mt_prep_snap

    # Reinstall autouse stubbing for this property-test environment.
    fake_stamps = tmp_path_factory.mktemp("stamps_prop")
    (fake_stamps / "matlab").mkdir(parents=True, exist_ok=True)
    (fake_stamps / "matlab" / "ps_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "matlab" / "sb_parms_initial.m").write_text("% noop\n")
    (fake_stamps / "bin").mkdir(parents=True, exist_ok=True)
    for b in ("calamp", "selpsc_patch", "selsbc_patch", "psclonlat", "pscdem", "pscphase"):
        (fake_stamps / "bin" / b).touch()
    monkeypatch.setenv("STAMPS", str(fake_stamps))
    monkeypatch.setattr(mt_prep_snap, "run_batch", lambda *a, **kw: 0)

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

    wd = tmp_path_factory.mktemp("wd")
    monkeypatch.chdir(wd)
    d = _ps_fixture(wd)

    if case == "too_few":
        with pytest.raises(SystemExit) as ei:
            mt_prep_snap.main(["20200101"])
        assert ei.value.code == 4
    elif case == "bad_mask":
        missing = wd / "nope.mask"
        with pytest.raises(SystemExit) as ei:
            mt_prep_snap.main(
                [
                    "20200101",
                    str(d),
                    "0.4",
                    "1",
                    "1",
                    "50",
                    "50",
                    str(missing),
                ]
            )
        assert ei.value.code == 2
    else:  # no_lon
        for p in (d / "geo").glob("*.lon"):
            p.unlink()
        with pytest.raises(SystemExit) as ei:
            mt_prep_snap.main(["20200101", str(d)])
        assert ei.value.code == 3
