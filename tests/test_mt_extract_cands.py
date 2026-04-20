"""Argument parsing + binary-dispatch tests for mt_extract_cands.py.

The 18 tests below mirror Task 2b.2 in the Windows port plan:
- Tests 37-48: argument parsing (12 tests).
- Tests 49-54: per-patch binary dispatch (6 tests).

Binary-dispatch tests mock subprocess.run via monkeypatch so no actual
C++ binary is invoked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stage a fake $STAMPS/bin with every binary the port may dispatch."""
    stamps_root = tmp_path / "stamps_root"
    bin_dir = stamps_root / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("selpsc_patch", "selsbc_patch", "psclonlat", "pscdem", "pscphase"):
        (bin_dir / name).write_text("#!/bin/sh\nexit 0\n")
        (bin_dir / name).chmod(0o755)
    monkeypatch.setenv("STAMPS", str(stamps_root))
    return stamps_root


def _make_workdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patches: list[str] | None = None,
    list_name: str = "patch.list",
    selsbc: bool = False,
) -> Path:
    """Create a workdir under tmp_path with patch.list + patch dirs, cd into it."""
    workdir = tmp_path / "work"
    workdir.mkdir()
    patches = patches if patches is not None else ["PATCH_1"]
    for p in patches:
        (workdir / p).mkdir()
    (workdir / list_name).write_text("\n".join(patches) + "\n")
    if selsbc:
        (workdir / "selsbc.in").write_text("100\n")
    else:
        (workdir / "selpsc.in").write_text("100\n")
    monkeypatch.chdir(workdir)
    return workdir


def _spy_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Install a MagicMock for subprocess.run inside mt_extract_cands."""
    import stamps.mt_extract_cands as mec

    spy = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(mec.subprocess, "run", spy)
    return spy


# ---------------------------------------------------------------------------
# Argument parsing (Tests 37-48)
# ---------------------------------------------------------------------------


def test_argc_zero_sets_all_four_flags_to_one(tmp_path, monkeypatch):
    """Test 37: argv=[] → dophase=dolonlat=dodem=docands=1 (csh L79-86)."""
    from stamps.mt_extract_cands import _parse_args

    args = _parse_args([])
    assert args["dophase"] == 1
    assert args["dolonlat"] == 1
    assert args["dodem"] == 1
    assert args["docands"] == 1


def test_argc_one_sets_only_dophase(tmp_path, monkeypatch):
    """Test 38: argv=["1"] → dophase=1, others=0 (KEY PORTING BUG CATCH, csh L34-86)."""
    from stamps.mt_extract_cands import _parse_args

    args = _parse_args(["1"])
    assert args["dophase"] == 1
    assert args["dolonlat"] == 0
    assert args["dodem"] == 0
    assert args["docands"] == 0


def test_explicit_zeros_disable_all(tmp_path, monkeypatch):
    """Test 39: argv=["0","0","0","0"] → no per-patch work."""
    _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    rc = main(["0", "0", "0", "0"])
    assert rc == 0
    assert spy.call_count == 0


def test_precision_default_is_f(tmp_path, monkeypatch):
    """Test 40: no precision argv → f (csh L54-56)."""
    from stamps.mt_extract_cands import _parse_args

    args = _parse_args(["1", "0", "0", "1"])
    assert args["prec"] == "f"


def test_precision_s_passed_through(tmp_path, monkeypatch):
    """Test 41: precision=s reaches command line (csh L52-53)."""
    _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1", "s", "0"])
    assert spy.call_count == 1
    cmd = spy.call_args_list[0].args[0]
    assert "s" in cmd
    assert "f" not in cmd


def test_byteswap_default_zero(tmp_path, monkeypatch):
    """Test 42: byteswap default = 0 (csh L59-62)."""
    from stamps.mt_extract_cands import _parse_args

    args = _parse_args(["1", "0", "0", "1", "f"])
    assert args["byteswap"] == 0


def test_byteswap_one_passed_through(tmp_path, monkeypatch):
    """Test 43: byteswap=1 reaches command line (csh L58-60)."""
    _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1", "f", "1"])
    cmd = spy.call_args_list[0].args[0]
    assert "1" in cmd


def test_maskfile_empty_invokes_without_argv(tmp_path, monkeypatch):
    """Test 44: empty maskfile → command does NOT append '' (csh L99-113)."""
    _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1", "f", "0", ""])
    cmd = spy.call_args_list[0].args[0]
    # No empty string trailing argv
    assert "" not in cmd
    # Command length = 8 (sel, sel_in, patch.in, pscands.1.ij, pscands.1.da,
    #                     mean_amp.flt, prec, byteswap), no mask suffix.
    assert len(cmd) == 8


def test_maskfile_nonempty_prefixed_with_workdir(tmp_path, monkeypatch):
    """Test 45: maskfile='mask.char' → passed as $WORKDIR/mask.char (csh L101,109)."""
    _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1", "f", "0", "mask.char"])
    cmd = spy.call_args_list[0].args[0]
    assert str(workdir / "mask.char") in cmd


def test_eight_args_uses_custom_patch_list(tmp_path, monkeypatch):
    """Test 46: 8th arg 'my.list' used (csh L70-76)."""
    _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch, list_name="my.list")
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    rc = main(["0", "0", "0", "1", "f", "0", "", "my.list"])
    assert rc == 0
    # default patch.list not present, so without honoring argv[7] we'd have crashed
    assert spy.call_count == 1


def test_seven_args_still_uses_default_patch_list(tmp_path, monkeypatch):
    """Test 47: argc==7 → patch.list used (regression >= vs == ; csh L70)."""
    _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch)
    # Stage a 'custom.list' that, if mistakenly used, would select PATCH_Z (absent).
    (workdir / "custom.list").write_text("PATCH_Z\n")
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    rc = main(["0", "0", "0", "1", "f", "0", ""])
    assert rc == 0
    # Confirm default patch.list was used (1 call for PATCH_1 present).
    assert spy.call_count == 1


def test_missing_patch_list_is_fatal(tmp_path, monkeypatch):
    """Test 48: no patch.list → FileNotFoundError (csh L91)."""
    _setup_env(tmp_path, monkeypatch)
    workdir = tmp_path / "bare"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    from stamps.mt_extract_cands import main

    with pytest.raises(FileNotFoundError):
        main([])


# ---------------------------------------------------------------------------
# Binary dispatch (Tests 49-54)
# ---------------------------------------------------------------------------


def test_selsbc_called_when_selsbc_in_exists(tmp_path, monkeypatch):
    """Test 49: selsbc.in present → selsbc_patch invoked (csh L98)."""
    stamps_root = _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch, selsbc=True)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1"])
    cmd = spy.call_args_list[0].args[0]
    assert cmd[0] == str(stamps_root / "bin" / "selsbc_patch")


def test_selpsc_called_otherwise(tmp_path, monkeypatch):
    """Test 50: no selsbc.in → selpsc_patch invoked (csh L106)."""
    stamps_root = _setup_env(tmp_path, monkeypatch)
    _make_workdir(tmp_path, monkeypatch, selsbc=False)
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "0", "1"])
    cmd = spy.call_args_list[0].args[0]
    assert cmd[0] == str(stamps_root / "bin" / "selpsc_patch")


def test_per_patch_cwd_kwarg_used(tmp_path, monkeypatch):
    """Test 51: every subprocess.run uses cwd=patch_dir; NO os.chdir (csh L88,93,138)."""
    _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch, patches=["PATCH_1", "PATCH_2"])
    # Stage supporting inputs so lonlat+dem+phase phases can compute correctly.
    (workdir / "psclonlat.in").write_text("x\n")
    (workdir / "pscdem.in").write_text("x\n")
    (workdir / "pscphase.in").write_text("x\n")
    import stamps.mt_extract_cands as mec

    spy = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(mec.subprocess, "run", spy)
    # Also assert os.chdir is never called by the implementation:
    chdir_spy = MagicMock()
    monkeypatch.setattr("os.chdir", chdir_spy)

    before = Path.cwd()
    mec.main([])  # All four flags = 1
    after = Path.cwd()
    assert before == after, "implementation must not leave cwd changed"

    # Every subprocess.run call must carry cwd=patch_dir.
    assert spy.call_count > 0
    expected_cwds = {workdir / "PATCH_1", workdir / "PATCH_2"}
    seen_cwds = set()
    for call in spy.call_args_list:
        assert "cwd" in call.kwargs, f"missing cwd kwarg in call {call}"
        seen_cwds.add(Path(call.kwargs["cwd"]))
    assert seen_cwds == expected_cwds
    # And os.chdir was never called.
    assert chdir_spy.call_count == 0


def test_psclonlat_invoked_when_dolonlat(tmp_path, monkeypatch):
    """Test 52: psclonlat_path psclonlat.in pscands.1.ij pscands.1.ll (csh L117-122)."""
    stamps_root = _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch)
    (workdir / "psclonlat.in").write_text("x\n")
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "1", "0", "0"])
    assert spy.call_count == 1
    cmd = spy.call_args_list[0].args[0]
    assert cmd == [
        str(stamps_root / "bin" / "psclonlat"),
        str(workdir / "psclonlat.in"),
        "pscands.1.ij",
        "pscands.1.ll",
    ]


def test_pscdem_invoked_when_dodem(tmp_path, monkeypatch):
    """Test 53: pscdem_path pscdem.in pscands.1.ij pscands.1.hgt (csh L124-129)."""
    stamps_root = _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch)
    (workdir / "pscdem.in").write_text("x\n")
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["0", "0", "1", "0"])
    assert spy.call_count == 1
    cmd = spy.call_args_list[0].args[0]
    assert cmd == [
        str(stamps_root / "bin" / "pscdem"),
        str(workdir / "pscdem.in"),
        "pscands.1.ij",
        "pscands.1.hgt",
    ]


def test_pscphase_invoked_when_dophase(tmp_path, monkeypatch):
    """Test 54: pscphase_path pscphase.in pscands.1.ij pscands.1.ph (csh L131-136)."""
    stamps_root = _setup_env(tmp_path, monkeypatch)
    workdir = _make_workdir(tmp_path, monkeypatch)
    (workdir / "pscphase.in").write_text("x\n")
    spy = _spy_run(monkeypatch)
    from stamps.mt_extract_cands import main

    main(["1", "0", "0", "0"])
    assert spy.call_count == 1
    cmd = spy.call_args_list[0].args[0]
    assert cmd == [
        str(stamps_root / "bin" / "pscphase"),
        str(workdir / "pscphase.in"),
        "pscands.1.ij",
        "pscands.1.ph",
    ]
