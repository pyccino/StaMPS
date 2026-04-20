"""Python port of bin/mt_prep_snap (csh).

Preserves csh semantics line-for-line:

* exit(4) on < 2 args, exit(2) on missing maskfile, exit(3) on no .lon
* integer division truncates toward zero (csh `@` operator)
* patch coords clamped to [1 .. width] / [1 .. length]
* iaz loop resets between irg iterations
* SB `RSC` picks the LAST sorted par match (gawk END), PS picks first
* psclonlat.in uses `head -1` (FIRST sorted)
* LF-only line endings across platforms
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ._log import banner, blank_line
from ._matlab import run_batch
from ._par import parse_par
from ._paths import check_locale, resolve_bin, stamps_root
from ._shell import (
    append_glob,  # noqa: F401 (API parity; available for downstream)
    append_text_lf,
    mkdir_if_missing,
    rm_rf_glob,
    sorted_glob,
    write_text_for_cpp,
    write_text_lf,
)

AUTHOR = "Andy Hooper, August 2017"

USAGE = (
    "usage: mt_prep_snap yyyymmdd datadir da_thresh "
    "[rg_patches az_patches rg_overlap az_overlap maskfile]\n"
    "    yyyymmdd                 = master date\n"
    "    datadir                  = data directory (with expected structure)\n"
    "    da_thresh                = (delta) amplitude dispersion threshold\n"
    "                                typical values: 0.4 for PS, 0.6 for SB\n"
    "    rg_patches (default 1)   = number of patches in range\n"
    "    az_patches (default 1)   = number of patches in azimuth\n"
    "    rg_overlap (default 50)  = overlapping pixels between patches in range\n"
    "    az_overlap (default 50) = overlapping pixels between patches in azimuth\n"
    "    maskfile (optional) char file, same dimensions as slcs, "
    "0 to include, 1 otherwise\n"
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    # csh: `if ($#argv < 2) ... exit(4)`.  $#argv is "number of positional
    # args", mapping to len(argv) when argv excludes the program name.
    if len(argv) < 2:
        sys.stderr.write(USAGE)
        sys.exit(4)
    ns = argparse.Namespace(
        master=argv[0],
        datadir=Path(argv[1]),
        da_thresh=None,
        prg=1,
        paz=1,
        overlap_rg=50,
        overlap_az=50,
        maskfile="",
    )
    if len(argv) > 2:
        ns.da_thresh = argv[2]
    if len(argv) > 3:
        ns.prg = int(argv[3])
    if len(argv) > 4:
        ns.paz = int(argv[4])
    if len(argv) > 5:
        ns.overlap_rg = int(argv[5])
    if len(argv) > 6:
        ns.overlap_az = int(argv[6])
    if len(argv) > 7:
        ns.maskfile = argv[7]
        if not Path(ns.maskfile).exists():
            print(f"{ns.maskfile} does not exist, exiting")
            sys.exit(2)
    return ns


def _csh_int_div(a: int, b: int) -> int:
    """csh @ truncates toward zero; Python // floor-divides. Use int(a/b).

    For non-negative operands this is equivalent to // but kept distinct
    so future sign-bearing inputs match csh exactly.
    """
    return int(a / b)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    banner("mt_prep_snap", AUTHOR)
    check_locale()
    args = _parse_args(argv)

    workdir = Path.cwd()
    sb_dir = args.datadir / "SMALL_BASELINES"
    sb_flag = sb_dir.exists()

    if sb_flag:
        print("Small Baseline Processing")
        blank_line()
        # csh gawk 'END {print $1}' → LAST sorted match.
        matches = sorted_glob(args.datadir / "SMALL_BASELINES" / "*" / f"{args.master}.*slc.par")
        if not matches:
            print(f"No RSC for master {args.master}", file=sys.stderr)
            sys.exit(3)
        rsc = matches[-1]
        print(rsc)
    else:
        matches = sorted_glob(args.datadir / "*slc" / f"{args.master}.*slc.par")
        if not matches:
            print(f"No RSC for master {args.master}", file=sys.stderr)
            sys.exit(3)
        rsc = matches[0]

    if args.da_thresh is None:
        args.da_thresh = "0.6" if sb_flag else "0.4"
    print(f"Amplitude Dispersion Threshold: {args.da_thresh}")
    print(f"Processing {args.prg} patch(es) in range and " f"{args.paz} in azimuth")
    blank_line()

    par = parse_par(rsc)
    length = int(par["azimuth_lines"])
    width = int(par["range_samples"])

    write_text_lf(workdir / "processor.txt", "snap\n")

    stamps_dir = stamps_root()
    script = stamps_dir / "matlab" / ("sb_parms_initial.m" if sb_flag else "ps_parms_initial.m")
    log = workdir / ("sb_parms_initial.log" if sb_flag else "ps_parms_initial.log")
    run_batch(script, log)

    write_text_lf(workdir / "width.txt", f"{width}\n")
    write_text_lf(workdir / "len.txt", f"{length}\n")
    write_text_lf(workdir / "rsc.txt", f"{rsc}\n")

    # calamp.in — list of SLC paths (LF, C++-readable on Windows).
    calamp_in = workdir / "calamp.in"
    calamp_in.unlink(missing_ok=True)
    slc_pattern = (
        args.datadir / "SMALL_BASELINES" / "*" / "*.*slc"
        if sb_flag
        else args.datadir / "*slc" / "*.*slc"
    )
    slc_list = sorted_glob(slc_pattern)
    write_text_for_cpp(
        calamp_in,
        ("\n".join(str(p) for p in slc_list) + "\n") if slc_list else "",
    )

    # Selfile header: da_thresh, width (calamp.out appended after calamp).
    selfile = workdir / ("selsbc.in" if sb_flag else "selpsc.in")
    write_text_lf(selfile, f"{args.da_thresh}\n{width}\n")

    # Run calamp — pass maskfile only when user gave one; never append "".
    calamp_exe = resolve_bin("calamp")
    calamp_args = [
        str(calamp_exe),
        str(calamp_in),
        str(width),
        str(workdir / "calamp.out"),
        "f",
        "1",
    ]
    if args.maskfile:
        calamp_args.append(args.maskfile)
    subprocess.run(calamp_args, check=True)

    # Append calamp.out to selfile.
    calamp_out = workdir / "calamp.out"
    if calamp_out.exists():
        with open(selfile, "ab") as sf:
            sf.write(calamp_out.read_bytes())

    # Patch tiling — csh `@` is truncating int div.
    width_p = _csh_int_div(width, args.prg)
    length_p = _csh_int_div(length, args.paz)
    rm_rf_glob(workdir / "PATCH_*")
    (workdir / "patch.list").unlink(missing_ok=True)
    ip = 0
    patches: list[str] = []
    for irg in range(1, args.prg + 1):
        # iaz resets between irg iterations (csh `set iaz = 0` after inner while).
        for iaz in range(1, args.paz + 1):
            ip += 1
            start_rg1 = width_p * (irg - 1) + 1
            start_rg = max(1, start_rg1 - args.overlap_rg)
            end_rg1 = width_p * irg
            end_rg = min(width, end_rg1 + args.overlap_rg)
            start_az1 = length_p * (iaz - 1) + 1
            start_az = max(1, start_az1 - args.overlap_az)
            end_az1 = length_p * iaz
            end_az = min(length, end_az1 + args.overlap_az)

            patch_dir = workdir / f"PATCH_{ip}"
            mkdir_if_missing(patch_dir)
            write_text_lf(
                patch_dir / "patch.in",
                f"{start_rg}\n{end_rg}\n{start_az}\n{end_az}\n",
            )
            write_text_lf(
                patch_dir / "patch_noover.in",
                f"{start_rg1}\n{end_rg1}\n{start_az1}\n{end_az1}\n",
            )
            patches.append(f"PATCH_{ip}")

    write_text_lf(workdir / "patch.list", "\n".join(patches) + "\n")

    # pscphase.in
    psc_in = workdir / "pscphase.in"
    write_text_lf(psc_in, f"{width}\n")
    diff_pattern = (
        args.datadir / "SMALL_BASELINES" / "*" / "*.diff"
        if sb_flag
        else args.datadir / "diff0" / "*.diff"
    )
    diffs = sorted_glob(diff_pattern)
    if diffs:
        append_text_lf(psc_in, "\n".join(str(d) for d in diffs) + "\n")

    # pscdem.in
    dem_in = workdir / "pscdem.in"
    write_text_lf(dem_in, f"{width}\n")
    dems = sorted_glob(args.datadir / "geo" / "*dem.rdc")
    if dems:
        append_text_lf(dem_in, "\n".join(str(d) for d in dems) + "\n")

    # psclonlat.in — csh `head -1` → FIRST sorted (distinct from gawk END).
    lons = sorted_glob(args.datadir / "geo" / "*.lon")
    if not lons:
        print("lon file does not exist")
        sys.exit(3)
    lats = sorted_glob(args.datadir / "geo" / "*.lat")
    lat0 = str(lats[0]) if lats else ""
    write_text_lf(
        workdir / "psclonlat.in",
        f"{width}\n{lons[0]}\n{lat0}\n" if lat0 else f"{width}\n{lons[0]}\n",
    )

    # Hand off to mt_extract_cands.
    from . import mt_extract_cands as mec

    mec_argv = ["1", "1", "1", "1", "f", "1"]
    if args.maskfile:
        mec_argv.append(args.maskfile)
    return mec.main(mec_argv)


if __name__ == "__main__":
    raise SystemExit(main())
