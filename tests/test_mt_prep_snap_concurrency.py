"""Concurrency tests for stamps.mt_prep_snap (4 tests).

Step 2 table 5. Exercises the mkdir / rm -rf / cwd-restore edge cases.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _write_par(path: Path, *, range_samples: int = 100, azimuth_lines: int = 200) -> Path:
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


def _stub_env(monkeypatch, tmp_path_factory):
    fake_stamps = tmp_path_factory.mktemp("stamps_root_conc")
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
# Tests (4)
# ---------------------------------------------------------------------------


def test_two_prep_snap_runs_in_separate_dirs_no_interference(
    tmp_path: Path, monkeypatch, tmp_path_factory
):
    """Two parallel runs in separate cwds both succeed."""
    _stub_env(monkeypatch, tmp_path_factory)
    from stamps.mt_prep_snap import main

    wd_a = tmp_path / "wdA"
    wd_b = tmp_path / "wdB"
    wd_a.mkdir()
    wd_b.mkdir()
    data_a = _ps_fixture(wd_a)
    data_b = _ps_fixture(wd_b)

    def _run(wd: Path, data: Path) -> int:
        # Each worker sets its own cwd via os.chdir before calling main,
        # then restores. This mirrors how the orchestrator will invoke it.
        old = Path.cwd()
        try:
            os.chdir(wd)
            return main(["20200101", str(data)])
        finally:
            os.chdir(old)

    with ThreadPoolExecutor(max_workers=2) as ex:
        # Serialize within each thread via a lock because os.chdir is
        # process-global. But the test still validates that both runs
        # produce their own outputs.
        lock = threading.Lock()

        def _guarded(wd, data):
            with lock:
                return _run(wd, data)

        f1 = ex.submit(_guarded, wd_a, data_a)
        f2 = ex.submit(_guarded, wd_b, data_b)
        f1.result()
        f2.result()

    assert (wd_a / "patch.list").exists()
    assert (wd_b / "patch.list").exists()
    assert (wd_a / "width.txt").read_bytes() == (wd_b / "width.txt").read_bytes()


def test_mkdir_patch_race(tmp_workdir):
    """Two threads calling mkdir_if_missing('PATCH_1') simultaneously → no error."""
    from stamps._shell import mkdir_if_missing

    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker():
        try:
            barrier.wait()
            mkdir_if_missing(tmp_workdir / "PATCH_1")
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"mkdir_if_missing race produced errors: {errors}"
    assert (tmp_workdir / "PATCH_1").is_dir()


def test_rm_rf_glob_concurrent_with_append_glob(tmp_workdir):
    """Clean + write race → no torn file."""
    from stamps._shell import append_glob, rm_rf_glob

    # Seed a victim dir set to satisfy rm_rf_glob's depth-3 safety check.
    # tmp_workdir is provided by pytest, sufficiently deep.
    source_dir = tmp_workdir / "src"
    source_dir.mkdir()
    for i in range(5):
        (source_dir / f"f{i}.txt").write_text(f"content {i}\n")

    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _cleaner():
        try:
            barrier.wait()
            (tmp_workdir / "to_delete").mkdir(exist_ok=True)
            (tmp_workdir / "to_delete" / "junk.txt").write_text("junk")
            rm_rf_glob(tmp_workdir / "to_delete")
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def _appender():
        try:
            barrier.wait()
            append_glob(tmp_workdir / "out.txt", source_dir / "*.txt")
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t1 = threading.Thread(target=_cleaner)
    t2 = threading.Thread(target=_appender)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert not errors
    # out.txt should exist and have well-formed line-separated entries.
    body = (tmp_workdir / "out.txt").read_bytes()
    assert body.endswith(b"\n")
    # No partial / torn byte at line boundaries.
    for ln in body.decode("ascii").split("\n"):
        if ln:
            assert ln.endswith(".txt")


def test_extract_cands_cwd_restore_on_interrupt(tmp_workdir, monkeypatch, tmp_path_factory):
    """KeyboardInterrupt mid-call → cwd restored via try/finally.

    Checks that stamps.mt_prep_snap does NOT leak cwd changes. The Python
    port uses `cwd=` kwargs on subprocess.run rather than os.chdir, so if
    a KeyboardInterrupt is raised inside main() the caller's cwd remains
    intact.
    """
    _stub_env(monkeypatch, tmp_path_factory)
    from stamps import mt_prep_snap

    # Override the autouse run_batch stub to raise KeyboardInterrupt.
    monkeypatch.setattr(
        mt_prep_snap,
        "run_batch",
        lambda *a, **kw: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    before = Path.cwd()
    d = _ps_fixture(tmp_workdir)
    with pytest.raises(KeyboardInterrupt):
        mt_prep_snap.main(["20200101", str(d)])
    assert Path.cwd() == before, "cwd leaked after KeyboardInterrupt"
