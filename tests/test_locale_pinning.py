"""Binaries must emit C-locale floats regardless of user locale."""
import os
import subprocess
from pathlib import Path

import pytest


BINARIES = ["calamp", "cpxsum", "pscphase", "pscdem",
            "psclonlat", "selpsc_patch", "selsbc_patch"]


@pytest.mark.parametrize("name", BINARIES)
def test_binary_starts_under_italian_locale(name: str, bin_dir: Path):
    """Each binary must start cleanly under Italian locale (no abort, banner prints).

    Some binaries (cpxsum) exit 0 on the no-args path; others exit nonzero.
    We only check that (a) the process runs to completion (no SIGABRT/segfault)
    and (b) at least one output stream has bytes — proving the C-locale pin
    didn't corrupt early stdio.
    """
    exe = bin_dir / (f"{name}.exe" if os.name == "nt" else name)
    if not exe.exists():
        pytest.skip(f"{exe} not built yet")
    env = os.environ.copy()
    env.update({"LC_ALL": "it_IT.UTF-8", "LC_NUMERIC": "it_IT.UTF-8"})
    proc = subprocess.run([str(exe)], capture_output=True, timeout=5, env=env)
    # No abort/segfault: returncode must be in [0, 255]. Negative values on
    # POSIX indicate the process was killed by a signal.
    assert 0 <= proc.returncode < 256, (
        f"{name} aborted (returncode={proc.returncode}, "
        f"likely SIGABRT/SIGSEGV)"
    )
    assert proc.stdout or proc.stderr, f"{name} produced no output"


def test_calamp_output_uses_dot_decimal_under_italian_locale(
    tmp_workdir: Path, bin_dir: Path
):
    """Calamp under Italian locale must NOT emit comma-decimal floats.

    Calamp's actual CLI: `calamp parmfile.in width parmfile.out precision
    byteswap [maskfile]` — arg1 is a TEXT listing of SLCs (one path per
    line), arg2 is width, arg3 is the output listing (calib factors per
    SLC), arg4 is precision ('f' or 's'), arg5 is byteswap (0 or 1).

    We build a 4-pixel × 1-line SLC + a parmfile.in pointing at it, run
    under it_IT locale, then inspect ALL output (stdout + stderr + the
    output text file) for any digit-comma-digit pattern. Comma-decimal
    floats from a stray printf would indicate the C-locale pin failed.
    """
    import re
    import struct
    exe = bin_dir / ("calamp.exe" if os.name == "nt" else "calamp")
    if not exe.exists():
        pytest.skip(f"{exe} not built yet")
    width = 4
    # 1 line × 4 pixels × complex_short (2× int16 LE) = 16 bytes
    slc = tmp_workdir / "tiny.slc"
    slc.write_bytes(struct.pack("<8h", 100, 200, 300, 400, 500, 600, 700, 800))
    parmfile_in = tmp_workdir / "calamp.in"
    parmfile_in.write_bytes(f"{slc}\n".encode())
    parmfile_out = tmp_workdir / "calamp.out"
    env = os.environ.copy()
    env.update({"LC_ALL": "it_IT.UTF-8", "LC_NUMERIC": "it_IT.UTF-8",
                "LANG": "it_IT.UTF-8"})
    proc = subprocess.run(
        [str(exe), str(parmfile_in), str(width),
         str(parmfile_out), "s", "0"],
        cwd=tmp_workdir, capture_output=True, timeout=10, env=env,
    )
    # Calamp's exit code on a valid run is 0; a failed open is nonzero.
    # If the binary itself fails on this fixture for unrelated reasons
    # (e.g., parmfile format drift), still inspect whatever output it
    # produced — comma-decimal in error text would equally indicate a
    # locale leak.
    streams = [proc.stdout, proc.stderr]
    if parmfile_out.exists():
        streams.append(parmfile_out.read_bytes())
    combined = b"\n".join(streams).decode(errors="replace")
    decimal_comma = re.search(r"\d,\d", combined)
    assert decimal_comma is None, (
        f"Italian-locale decimal-comma leaked past the C-locale pin "
        f"(returncode={proc.returncode}): {decimal_comma.group(0)!r} "
        f"in {combined!r}"
    )
