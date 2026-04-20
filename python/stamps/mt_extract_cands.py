"""Python port of bin/mt_extract_cands (csh)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ._log import banner, blank_line
from ._paths import resolve_bin

AUTHOR = "Andy Hooper, Jan 2007"


def _parse_args(argv: list[str]) -> dict[str, Any]:
    """Matches csh: argc==0 → all four flags = 1; argc≥1 → only args win, rest 0."""
    defaults = {
        "dophase": 0,
        "dolonlat": 0,
        "dodem": 0,
        "docands": 0,
        "prec": "f",
        "byteswap": 0,
        "maskfile": "",
        "list": "patch.list",
    }
    if not argv:
        return {**defaults, "dophase": 1, "dolonlat": 1, "dodem": 1, "docands": 1}
    if len(argv) == 8:
        defaults["list"] = argv[7]
    int_keys = {"dophase", "dolonlat", "dodem", "docands", "byteswap"}
    keys = ["dophase", "dolonlat", "dodem", "docands", "prec", "byteswap", "maskfile"]
    for i, k in enumerate(keys):
        if i >= len(argv):
            break
        defaults[k] = int(argv[i]) if k in int_keys else argv[i]
    return defaults


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    banner("mt_extract_cands", AUTHOR)
    blank_line()
    args = _parse_args(argv)
    workdir = Path.cwd()

    list_path = workdir / args["list"]
    if not list_path.exists():
        raise FileNotFoundError(list_path)
    patches = list_path.read_text().split()
    use_selsbc = (workdir / "selsbc.in").exists()

    for patch in patches:
        patch_dir = workdir / patch
        print(f"\nPatch: {patch}")

        if args["docands"]:
            if use_selsbc:
                sel = resolve_bin("selsbc_patch")
                sel_in = workdir / "selsbc.in"
            else:
                sel = resolve_bin("selpsc_patch")
                sel_in = workdir / "selpsc.in"
            cmd = [
                str(sel),
                str(sel_in),
                "patch.in",
                "pscands.1.ij",
                "pscands.1.da",
                "mean_amp.flt",
                args["prec"],
                str(args["byteswap"]),
            ]
            if args["maskfile"]:
                cmd.append(str(workdir / args["maskfile"]))
            print(" ".join(cmd))
            subprocess.run(cmd, cwd=patch_dir, check=False)

        if args["dolonlat"]:
            subprocess.run(
                [
                    str(resolve_bin("psclonlat")),
                    str(workdir / "psclonlat.in"),
                    "pscands.1.ij",
                    "pscands.1.ll",
                ],
                cwd=patch_dir,
                check=False,
            )

        if args["dodem"]:
            subprocess.run(
                [
                    str(resolve_bin("pscdem")),
                    str(workdir / "pscdem.in"),
                    "pscands.1.ij",
                    "pscands.1.hgt",
                ],
                cwd=patch_dir,
                check=False,
            )

        if args["dophase"]:
            subprocess.run(
                [
                    str(resolve_bin("pscphase")),
                    str(workdir / "pscphase.in"),
                    "pscands.1.ij",
                    "pscands.1.ph",
                ],
                cwd=patch_dir,
                check=False,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
