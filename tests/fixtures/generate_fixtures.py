"""Deterministic synthetic SAR fixtures.

Seed: 0x57414D50 (b"STAMP" as 4 ASCII bytes).
Random: stdlib random.Random(seed).
Binary: struct.pack('<f', ...) for float32; struct.pack('<B', ...) for uint8.
"""

import random
import struct
from pathlib import Path

SEED = 0x57414D50
WIDTH = 200
LENGTH = 200
N_IMAGES = 3

# Trimmed dimensions for --small (used by nightly E2E + PHASE integration tests
# where the 200x200 x 5-raster default makes wall-clock budgets spill). Same
# raster layout, same acquisition dates, same seed — only the per-raster
# byte footprint shrinks, so ``stamps(1,7)`` still has meaningful PS candidates
# to work with (20x20 = 400 px ~= 40-120 PS after amplitude dispersion).
SMALL_WIDTH = 20
SMALL_LENGTH = 20

PAR_TEMPLATE = """azimuth_lines: {length}
range_samples: {width}
prf: 486.4863103
range_pixel_spacing: 2.329562
azimuth_pixel_spacing: 13.948919
radar_frequency: 5.3050000e+09
near_range_slc: 834018.0234
"""


def _gen_complex_raster(rng, width, length):
    """Generate a synthetic complex float32 raster with PS-like structure."""
    import math

    buf = bytearray()
    for i in range(length):
        for j in range(width):
            amp = 100.0 + 10.0 * math.sin(i / 20.0) + 5.0 * math.sin(j / 15.0) + rng.gauss(0, 2)
            phase = 2.0 * math.pi * (i + j) / 100.0
            re = amp * math.cos(phase)
            im = amp * math.sin(phase)
            buf.extend(struct.pack("<ff", re, im))
    return bytes(buf)


def _gen_float_raster(rng, width, length, kind):
    """Float32 raster: lon/lat/dem have different signals."""
    buf = bytearray()
    for i in range(length):
        for j in range(width):
            if kind == "lon":
                v = 12.5 + j * 0.001
            elif kind == "lat":
                v = 45.0 + i * 0.001
            else:  # dem
                v = 500.0 + 50.0 * (i + j) / (length + width)
            buf.extend(struct.pack("<f", v))
    return bytes(buf)


def _gen_mask(width, length):
    buf = bytearray()
    for i in range(length):
        for j in range(width):
            buf.append(1 if ((i // 8) + (j // 8)) % 2 == 0 else 0)
    return bytes(buf)


def _write_par(path, length, width):
    # write_bytes bypasses platform newline translation — Windows write_text
    # would emit CRLF and break the SHA256 manifest. Writing raw LF keeps the
    # fixture byte-identical across Linux/macOS/Windows.
    path.write_bytes(PAR_TEMPLATE.format(length=length, width=width).encode("ascii"))


def _write_baseline(path):
    path.write_bytes(
        b"BPERP:      50.0\nBTEMP:      12.0\n"
        b"HORIZONTAL: 10.0\nVERTICAL:   -5.0\n"
        b"PRECISION:  0.1\nREFERENCE:  0\n"
    )


def generate_ps_fixture(dest: Path, width: int = WIDTH, length: int = LENGTH):
    """Generate a PS-mode fixture tree.

    ``width`` / ``length`` default to the canonical 200x200 used by the
    committed fixture + SHA256 manifest in test_generate_fixtures.py.
    Pass ``SMALL_WIDTH`` / ``SMALL_LENGTH`` (20x20) for the trimmed
    ``--small`` variant driven by E2E / PHASE integration tests.
    """
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    (dest / "rslc").mkdir(exist_ok=True)
    (dest / "diff0").mkdir(exist_ok=True)
    (dest / "geo").mkdir(exist_ok=True)
    (dest / "dem").mkdir(exist_ok=True)
    (dest / "mask").mkdir(exist_ok=True)
    for date in ("20200101", "20200113", "20200125"):
        (dest / "rslc" / f"{date}.rslc").write_bytes(_gen_complex_raster(rng, width, length))
        _write_par(dest / "rslc" / f"{date}.rslc.par", length, width)
    for date in ("20200113", "20200125"):
        (dest / "diff0" / f"{date}.diff").write_bytes(_gen_complex_raster(rng, width, length))
        _write_baseline(dest / "diff0" / f"{date}.base")
    (dest / "geo" / "20200101.lon").write_bytes(_gen_float_raster(rng, width, length, "lon"))
    (dest / "geo" / "20200101.lat").write_bytes(_gen_float_raster(rng, width, length, "lat"))
    (dest / "geo" / "20200101_dem.rdc").write_bytes(_gen_float_raster(rng, width, length, "dem"))
    _write_par(dest / "geo" / "20200101.diff_par", length, width)
    _write_par(dest / "dem" / "20200101_seg.par", length, width)
    (dest / "mask" / "mask.char").write_bytes(_gen_mask(width, length))


def generate_sb_fixture(dest: Path, width: int = WIDTH, length: int = LENGTH):
    """Generate an SB-mode fixture tree. See ``generate_ps_fixture`` for
    the ``width`` / ``length`` contract."""
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    sb_root = dest / "SMALL_BASELINES"
    sb_root.mkdir(exist_ok=True)
    for pair in ("20200101_20200113", "20200101_20200125"):
        pd = sb_root / pair
        pd.mkdir(exist_ok=True)
        # both master and slave SLC
        master, slave = pair.split("_")
        (pd / f"{master}.rslc").write_bytes(_gen_complex_raster(rng, width, length))
        (pd / f"{slave}.rslc").write_bytes(_gen_complex_raster(rng, width, length))
        # Upstream csh mt_prep_snap detects SB via:
        #   \ls $datadir/SMALL_BASELINES/*/$master.*slc.par
        # which expects a MASTER-named .par file inside each pair dir, not
        # a pair-named one. Write both to be robust — the legacy script
        # picks up the first match; the Python port accepts either.
        _write_par(pd / f"{master}.rslc.par", length, width)
        _write_par(pd / f"{pair}.rslc.par", length, width)
        (pd / f"{pair}.diff").write_bytes(_gen_complex_raster(rng, width, length))
        _write_baseline(pd / f"{pair}.base")
    # Reuse geo + dem + mask from PS layout
    for sub in ("geo", "dem", "mask"):
        (dest / sub).mkdir(exist_ok=True)
    (dest / "geo" / "20200101.lon").write_bytes(_gen_float_raster(rng, width, length, "lon"))
    (dest / "geo" / "20200101.lat").write_bytes(_gen_float_raster(rng, width, length, "lat"))
    (dest / "geo" / "20200101_dem.rdc").write_bytes(_gen_float_raster(rng, width, length, "dem"))
    _write_par(dest / "geo" / "20200101.diff_par", length, width)
    _write_par(dest / "dem" / "20200101_seg.par", length, width)
    (dest / "mask" / "mask.char").write_bytes(_gen_mask(width, length))


def _sha256_tree(root: Path) -> dict:
    import hashlib

    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            # Use forward-slash POSIX keys so the manifest is
            # cross-platform. str(WindowsPath) uses backslashes, which
            # would make Windows keys diverge from Linux keys.
            rel = p.relative_to(root).as_posix()
            out[rel] = h
    return out


def _main(argv: list[str] | None = None) -> int:
    """CLI entry point. Parsed with argparse (stdlib) to keep the
    generator dependency-free per plan policy §7.

    Two modes:
      * default (no flags): emit ``synthetic_ps`` + ``synthetic_sb`` at
        200x200. Byte-locked against ``test_generate_fixtures.py``.
      * ``--small``: emit ``synthetic_ps_small`` + ``synthetic_sb_small``
        at 20x20. Consumed by nightly E2E / PHASE integration tests; NOT
        byte-locked (dimensions may evolve as test coverage grows).
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic SAR fixtures for StaMPS tests.",
    )
    # Keyword-only ``--out`` (no positional form). Previous revisions accepted
    # both an ``out`` positional and an ``--out`` flag, which was redundant and
    # confusing at the CLI; the flag form is self-documenting, so we keep only
    # that one. All in-tree callers (conftest.py, tests/golden/capture.sh,
    # nightly-e2e.yml / ci.yml) either import the Python API or invoke without
    # arguments, so no caller update is required.
    parser.add_argument(
        "--out",
        dest="out",
        default="tests/fixtures",
        help="Output directory (default: tests/fixtures).",
    )
    parser.add_argument(
        "--small",
        action="store_true",
        help=(
            f"Emit trimmed {SMALL_WIDTH}x{SMALL_LENGTH} fixtures "
            "(synthetic_ps_small, synthetic_sb_small) instead of the "
            "default 200x200 ones. Used by nightly E2E + PHASE→StaMPS "
            "integration tests."
        ),
    )
    args = parser.parse_args(argv)

    dest = Path(args.out)
    if args.small:
        ps_name, sb_name = "synthetic_ps_small", "synthetic_sb_small"
        width, length = SMALL_WIDTH, SMALL_LENGTH
    else:
        ps_name, sb_name = "synthetic_ps", "synthetic_sb"
        width, length = WIDTH, LENGTH

    generate_ps_fixture(dest / ps_name, width=width, length=length)
    generate_sb_fixture(dest / sb_name, width=width, length=length)
    print(
        json.dumps(
            {
                "ps": _sha256_tree(dest / ps_name),
                "sb": _sha256_tree(dest / sb_name),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv[1:]))
