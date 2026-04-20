"""Deterministic fixture-generator regression test.

The generator at ``tests/fixtures/generate_fixtures.py`` must produce a
byte-identical tree every run (seed ``0x57414D50``). This test locks the
full SHA256 manifest for both PS and SB fixture trees so any accidental
change to the generator or its dependencies (stdlib only, per plan
policy §7) is caught immediately.

If this test fails after an intentional generator change, regenerate the
expected manifests with::

    python3 tests/fixtures/generate_fixtures.py --out /tmp/fx

and paste the resulting JSON into the constants below.
"""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from tests.fixtures.generate_fixtures import (
    _sha256_tree,
    generate_ps_fixture,
    generate_sb_fixture,
)

EXPECTED_PS = {
    "dem/20200101_seg.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "diff0/20200113.base": "1427808974eda60cfa6704274e7d3ecbc949edd7860d81460e551eb13d465dca",
    "diff0/20200113.diff": "4c382f0dcfe15f3fc1f61aa59b01693322902e4408e15ae3cf5da13d82fa90b1",
    "diff0/20200125.base": "1427808974eda60cfa6704274e7d3ecbc949edd7860d81460e551eb13d465dca",
    "diff0/20200125.diff": "aaae01dfb8579f6fcd6b8f438c88a6a340831652fc1bc5da83ba4b88924cedfd",
    "geo/20200101.diff_par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "geo/20200101.lat": "70d4d00a374bf38dd824ffb2a4925ad9a2f5a1c0989f2a620db084f615ecf71d",
    "geo/20200101.lon": "0b815768ecb698cc08a082b124134e8381c3e81407c9bdf0b90705c8972c9295",
    "geo/20200101_dem.rdc": "e7848cbc304676b8476f3e07955c2c59e545574bda70a97bf59445d79b5ac31c",
    "mask/mask.char": "2e859282cd1ce507d90160849b9e839cb699fa60bfecb8ed3b0733c324098b09",
    "rslc/20200101.rslc": "1127f470ca03ad1dcc026a55bc09bfe45cc651914ac164d88b966aef08950a1f",
    "rslc/20200101.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "rslc/20200113.rslc": "009ab36e96eddbfa2a24b484f96ba1f1f167ccd4d53453040cc42d7fbeade06b",
    "rslc/20200113.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "rslc/20200125.rslc": "0eb917002edabe5ca8f6a92932e29396d56eb26ccd4b28ad4cf6a543664d5b24",
    "rslc/20200125.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
}

EXPECTED_SB = {
    "SMALL_BASELINES/20200101_20200113/20200101.rslc": "1127f470ca03ad1dcc026a55bc09bfe45cc651914ac164d88b966aef08950a1f",
    # Generator now also emits a master-named .rslc.par per upstream
    # csh convention (mt_prep_snap looks up $master.*slc.par to detect SB
    # mode) alongside the pair-named one.
    "SMALL_BASELINES/20200101_20200113/20200101.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "SMALL_BASELINES/20200101_20200113/20200101_20200113.base": "1427808974eda60cfa6704274e7d3ecbc949edd7860d81460e551eb13d465dca",
    "SMALL_BASELINES/20200101_20200113/20200101_20200113.diff": "0eb917002edabe5ca8f6a92932e29396d56eb26ccd4b28ad4cf6a543664d5b24",
    "SMALL_BASELINES/20200101_20200113/20200101_20200113.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "SMALL_BASELINES/20200101_20200113/20200113.rslc": "009ab36e96eddbfa2a24b484f96ba1f1f167ccd4d53453040cc42d7fbeade06b",
    "SMALL_BASELINES/20200101_20200125/20200101.rslc": "4c382f0dcfe15f3fc1f61aa59b01693322902e4408e15ae3cf5da13d82fa90b1",
    "SMALL_BASELINES/20200101_20200125/20200101.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "SMALL_BASELINES/20200101_20200125/20200101_20200125.base": "1427808974eda60cfa6704274e7d3ecbc949edd7860d81460e551eb13d465dca",
    "SMALL_BASELINES/20200101_20200125/20200101_20200125.diff": "ae2780982e06dd75dc6829b755c90d3485a2e2662e4e9d9570da3006454d3c24",
    "SMALL_BASELINES/20200101_20200125/20200101_20200125.rslc.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "SMALL_BASELINES/20200101_20200125/20200125.rslc": "aaae01dfb8579f6fcd6b8f438c88a6a340831652fc1bc5da83ba4b88924cedfd",
    "dem/20200101_seg.par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "geo/20200101.diff_par": "0392222e73b667c7812f1b9c17456a71a21569d52086d1615b939377937bd4ba",
    "geo/20200101.lat": "70d4d00a374bf38dd824ffb2a4925ad9a2f5a1c0989f2a620db084f615ecf71d",
    "geo/20200101.lon": "0b815768ecb698cc08a082b124134e8381c3e81407c9bdf0b90705c8972c9295",
    "geo/20200101_dem.rdc": "e7848cbc304676b8476f3e07955c2c59e545574bda70a97bf59445d79b5ac31c",
    "mask/mask.char": "2e859282cd1ce507d90160849b9e839cb699fa60bfecb8ed3b0733c324098b09",
}

# Each raster is 200x200 complex-float32 (320000 B) or float32 (160000 B)
# or uint8 (40000 B). Verify the per-file byte counts too so "deterministic"
# actually means "deterministic and of the expected shape".
EXPECTED_SIZES_PS = {
    "rslc/20200101.rslc": 320000,
    "rslc/20200113.rslc": 320000,
    "rslc/20200125.rslc": 320000,
    "diff0/20200113.diff": 320000,
    "diff0/20200125.diff": 320000,
    "geo/20200101.lon": 160000,
    "geo/20200101.lat": 160000,
    "geo/20200101_dem.rdc": 160000,
    "mask/mask.char": 40000,
}


# The fixture generator uses random.Random(SEED).gauss(...) which depends on
# math.log + math.sqrt + math.cos — libm implementations diverge at the last
# bit across platforms (Linux glibc vs MinGW mingw-w64 vs macOS libSystem vs
# MSVC UCRT). The resulting .rslc / .diff raster bytes differ between them
# even with an identical random seed. Lock the manifest against Linux glibc
# (the canonical reference where goldens are captured in Task 2c.2); other
# platforms get the determinism check via the separate _determinism tests.
_LIBM_REFERENCE = platform.system() == "Linux" and platform.python_implementation() == "CPython"


@pytest.mark.skipif(
    not _LIBM_REFERENCE,
    reason="Manifest locked against Linux glibc libm; platform-specific last-bit "
    "float drift on MinGW/MSVC/macOS is expected and covered by determinism tests.",
)
def test_ps_fixture_sha256_manifest(tmp_path: Path) -> None:
    """PS-mode tree is byte-identical to the locked manifest."""
    dest = tmp_path / "synthetic_ps"
    generate_ps_fixture(dest)
    actual = _sha256_tree(dest)
    assert actual == EXPECTED_PS, (
        "PS fixture tree drifted from locked manifest; " "investigate before regenerating goldens."
    )


@pytest.mark.skipif(
    not _LIBM_REFERENCE,
    reason="Manifest locked against Linux glibc libm; platform-specific last-bit "
    "float drift on MinGW/MSVC/macOS is expected and covered by determinism tests.",
)
def test_sb_fixture_sha256_manifest(tmp_path: Path) -> None:
    """SB-mode tree is byte-identical to the locked manifest."""
    dest = tmp_path / "synthetic_sb"
    generate_sb_fixture(dest)
    actual = _sha256_tree(dest)
    assert actual == EXPECTED_SB, (
        "SB fixture tree drifted from locked manifest; " "investigate before regenerating goldens."
    )


def test_ps_fixture_determinism(tmp_path: Path) -> None:
    """Running the generator twice produces byte-identical output."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate_ps_fixture(a)
    generate_ps_fixture(b)
    assert _sha256_tree(a) == _sha256_tree(b)


def test_sb_fixture_determinism(tmp_path: Path) -> None:
    """Running the SB generator twice produces byte-identical output."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate_sb_fixture(a)
    generate_sb_fixture(b)
    assert _sha256_tree(a) == _sha256_tree(b)


def test_ps_raster_byte_sizes(tmp_path: Path) -> None:
    """Binary rasters have exactly the advertised dtype/shape footprint."""
    dest = tmp_path / "synthetic_ps"
    generate_ps_fixture(dest)
    for rel, expected_bytes in EXPECTED_SIZES_PS.items():
        actual = (dest / rel).stat().st_size
        assert actual == expected_bytes, f"{rel}: {actual} B, expected {expected_bytes} B"
