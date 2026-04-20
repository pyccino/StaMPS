"""Python port of bin/mt_extract_cands (csh)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ._log import banner, blank_line
from ._paths import resolve_bin

AUTHOR = "Andy Hooper, Jan 2007"

# Synthetic return code used when a patch directory is missing on disk. Chosen
# well outside the 0-255 range that POSIX subprocesses can return so it's
# distinguishable in the failure summary and in tests.
_MISSING_DIR_RC = -1


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


def _parse_patch_list(list_path: Path) -> list[str]:
    """Parse patch.list the same way csh `foreach patch(\\`cat $list\\`)` does.

    - Iterate by lines (not whitespace) — csh's backtick-cat respects lines.
    - Robust to CRLF via splitlines().
    - UTF-8-SIG encoding so non-ASCII directory names round-trip on Windows
      hosts AND a leading UTF-8 BOM (as SNAP sometimes emits on Windows) is
      transparently stripped. Without `-sig`, the BOM would appear as \ufeff
      at the head of the first patch name and break the subsequent cwd=patch_dir.
    - Skip blank lines and comment lines starting with '#'. csh doesn't support
      comments here, but neither does it choke on an unused extra line; this is
      a friendly extension.
    """
    text = list_path.read_text(encoding="utf-8-sig")
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _run_patch_step(
    cmd: list[str],
    patch_dir: Path,
    patch: str,
    binary_name: str,
    failed_patches: list[tuple[str, str, int]],
    *,
    leading_blank: bool = True,
) -> None:
    """Run one per-patch subprocess, recording failures instead of raising.

    Behavior difference from the csh original: csh silently continues on any
    per-patch failure (there's no `set -e` equivalent in the foreach loop, and
    each invocation is bare). The Python port collects failures and exits
    nonzero at the end so CI catches what csh would have swallowed.

    Also validates the patch directory exists before invoking subprocess;
    a missing dir is recorded as a synthetic failure (rc=_MISSING_DIR_RC) and
    the pipeline continues — never crashes with FileNotFoundError.
    """
    if not patch_dir.is_dir():
        failed_patches.append((patch, binary_name, _MISSING_DIR_RC))
        print(
            f"mt_extract_cands: patch directory missing: {patch_dir} (skipping {binary_name})",
            file=sys.stderr,
        )
        return
    if leading_blank:
        blank_line()
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=patch_dir, check=False)
    if result.returncode != 0:
        failed_patches.append((patch, binary_name, result.returncode))


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
    patches = _parse_patch_list(list_path)
    use_selsbc = (workdir / "selsbc.in").exists()

    # (patch_name, binary_name, returncode) for every non-zero rc or missing dir.
    failed_patches: list[tuple[str, str, int]] = []

    for patch in patches:
        patch_dir = workdir / patch
        print(f"\nPatch: {patch}")

        if args["docands"]:
            if use_selsbc:
                sel = resolve_bin("selsbc_patch")
                sel_in = workdir / "selsbc.in"
                sel_name = "selsbc_patch"
            else:
                sel = resolve_bin("selpsc_patch")
                sel_in = workdir / "selpsc.in"
                sel_name = "selpsc_patch"
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
            # csh does NOT emit an extra blank line before the selpsc/selsbc
            # echo (the "Patch:" banner above already supplied one).
            _run_patch_step(cmd, patch_dir, patch, sel_name, failed_patches, leading_blank=False)

        if args["dolonlat"]:
            cmd = [
                str(resolve_bin("psclonlat")),
                str(workdir / "psclonlat.in"),
                "pscands.1.ij",
                "pscands.1.ll",
            ]
            _run_patch_step(cmd, patch_dir, patch, "psclonlat", failed_patches)

        if args["dodem"]:
            cmd = [
                str(resolve_bin("pscdem")),
                str(workdir / "pscdem.in"),
                "pscands.1.ij",
                "pscands.1.hgt",
            ]
            _run_patch_step(cmd, patch_dir, patch, "pscdem", failed_patches)

        if args["dophase"]:
            cmd = [
                str(resolve_bin("pscphase")),
                str(workdir / "pscphase.in"),
                "pscands.1.ij",
                "pscands.1.ph",
            ]
            _run_patch_step(cmd, patch_dir, patch, "pscphase", failed_patches)

    if failed_patches:
        print(
            f"mt_extract_cands: {len(failed_patches)} per-patch step(s) failed:",
            file=sys.stderr,
        )
        for patch_name, binary_name, rc in failed_patches:
            print(f"  - {patch_name}: {binary_name} rc={rc}", file=sys.stderr)
        sys.exit(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
