"""Binaries must emit C-locale floats regardless of user locale."""
import os
import subprocess
from pathlib import Path

import pytest


BINARIES = ["calamp", "cpxsum", "pscphase", "pscdem",
            "psclonlat", "selpsc_patch", "selsbc_patch"]


@pytest.mark.parametrize("name", BINARIES)
def test_binary_starts_under_italian_locale(name: str, bin_dir: Path):
    exe = bin_dir / (f"{name}.exe" if os.name == "nt" else name)
    if not exe.exists():
        pytest.skip(f"{exe} not built yet")
    env = os.environ.copy()
    env.update({"LC_ALL": "it_IT.UTF-8", "LC_NUMERIC": "it_IT.UTF-8"})
    proc = subprocess.run([str(exe)], capture_output=True, timeout=5, env=env)
    # Usage path exits nonzero; banner still prints.
    assert proc.returncode != 0
    assert proc.stdout or proc.stderr


def test_calamp_output_uses_dot_decimal_under_italian_locale(
    tmp_workdir: Path, bin_dir: Path
):
    """Integration: run calamp on a minimal input; assert '.' in numeric output.

    Calamp accepts: <input.slc> <width> <byte_order> <output.amp>. Build a
    tiny 4-px-wide x 1-line synthetic SLC (8 bytes complex16-LE per pixel
    = 32 bytes) and run calamp under it_IT locale. Calamp prints the
    average amplitude to stdout. Assert the output contains '.' (NOT ',')
    as the decimal separator — the regression we're guarding against is
    Italian-locale builds emitting `1,234` instead of `1.234`.
    """
    import struct
    exe = bin_dir / ("calamp.exe" if os.name == "nt" else "calamp")
    if not exe.exists():
        pytest.skip(f"{exe} not built yet")
    width = 4
    # 1 line × 4 pixels × complex16 (2× int16 LE) = 16 bytes
    slc = tmp_workdir / "tiny.slc"
    slc.write_bytes(struct.pack("<8h", 100, 200, 300, 400, 500, 600, 700, 800))
    out_amp = tmp_workdir / "tiny.amp"
    env = os.environ.copy()
    env.update({"LC_ALL": "it_IT.UTF-8", "LC_NUMERIC": "it_IT.UTF-8",
                "LANG": "it_IT.UTF-8"})
    proc = subprocess.run(
        [str(exe), str(slc), str(width), "1", str(out_amp)],
        capture_output=True, timeout=10, env=env,
    )
    assert proc.returncode == 0, (
        f"calamp failed: stderr={proc.stderr!r} stdout={proc.stdout!r}"
    )
    combined = (proc.stdout + proc.stderr).decode(errors="replace")
    # Italian locale would produce '1,234' for the mean amplitude.
    # C-locale pin guarantees '1.234'. Assert both: dot present, comma not
    # used as a decimal separator (i.e., no digit-comma-digit sequence).
    import re
    assert "." in combined, (
        f"No dot decimal in calamp output under it_IT locale: {combined!r}"
    )
    decimal_comma = re.search(r"\d,\d", combined)
    assert decimal_comma is None, (
        f"Italian-locale decimal-comma leaked through C-locale pin: "
        f"{decimal_comma.group(0)!r} in {combined!r}"
    )
