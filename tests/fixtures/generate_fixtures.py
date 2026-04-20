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


def generate_ps_fixture(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    (dest / "rslc").mkdir(exist_ok=True)
    (dest / "diff0").mkdir(exist_ok=True)
    (dest / "geo").mkdir(exist_ok=True)
    (dest / "dem").mkdir(exist_ok=True)
    (dest / "mask").mkdir(exist_ok=True)
    for date in ("20200101", "20200113", "20200125"):
        (dest / "rslc" / f"{date}.rslc").write_bytes(_gen_complex_raster(rng, WIDTH, LENGTH))
        _write_par(dest / "rslc" / f"{date}.rslc.par", LENGTH, WIDTH)
    for date in ("20200113", "20200125"):
        (dest / "diff0" / f"{date}.diff").write_bytes(_gen_complex_raster(rng, WIDTH, LENGTH))
        _write_baseline(dest / "diff0" / f"{date}.base")
    (dest / "geo" / "20200101.lon").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "lon"))
    (dest / "geo" / "20200101.lat").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "lat"))
    (dest / "geo" / "20200101_dem.rdc").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "dem"))
    _write_par(dest / "geo" / "20200101.diff_par", LENGTH, WIDTH)
    _write_par(dest / "dem" / "20200101_seg.par", LENGTH, WIDTH)
    (dest / "mask" / "mask.char").write_bytes(_gen_mask(WIDTH, LENGTH))


def generate_sb_fixture(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    sb_root = dest / "SMALL_BASELINES"
    sb_root.mkdir(exist_ok=True)
    for pair in ("20200101_20200113", "20200101_20200125"):
        pd = sb_root / pair
        pd.mkdir(exist_ok=True)
        # both master and slave SLC
        master, slave = pair.split("_")
        (pd / f"{master}.rslc").write_bytes(_gen_complex_raster(rng, WIDTH, LENGTH))
        (pd / f"{slave}.rslc").write_bytes(_gen_complex_raster(rng, WIDTH, LENGTH))
        # Upstream csh mt_prep_snap detects SB via:
        #   \ls $datadir/SMALL_BASELINES/*/$master.*slc.par
        # which expects a MASTER-named .par file inside each pair dir, not
        # a pair-named one. Write both to be robust — the legacy script
        # picks up the first match; the Python port accepts either.
        _write_par(pd / f"{master}.rslc.par", LENGTH, WIDTH)
        _write_par(pd / f"{pair}.rslc.par", LENGTH, WIDTH)
        (pd / f"{pair}.diff").write_bytes(_gen_complex_raster(rng, WIDTH, LENGTH))
        _write_baseline(pd / f"{pair}.base")
    # Reuse geo + dem + mask from PS layout
    for sub in ("geo", "dem", "mask"):
        (dest / sub).mkdir(exist_ok=True)
    (dest / "geo" / "20200101.lon").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "lon"))
    (dest / "geo" / "20200101.lat").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "lat"))
    (dest / "geo" / "20200101_dem.rdc").write_bytes(_gen_float_raster(rng, WIDTH, LENGTH, "dem"))
    _write_par(dest / "geo" / "20200101.diff_par", LENGTH, WIDTH)
    _write_par(dest / "dem" / "20200101_seg.par", LENGTH, WIDTH)
    (dest / "mask" / "mask.char").write_bytes(_gen_mask(WIDTH, LENGTH))


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


if __name__ == "__main__":
    import json
    import sys

    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures")
    generate_ps_fixture(dest / "synthetic_ps")
    generate_sb_fixture(dest / "synthetic_sb")
    print(
        json.dumps(
            {
                "ps": _sha256_tree(dest / "synthetic_ps"),
                "sb": _sha256_tree(dest / "synthetic_sb"),
            },
            indent=2,
        )
    )
