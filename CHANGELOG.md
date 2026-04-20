# Changelog

All notable changes to the StaMPS Windows port are documented here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `tests/golden/linux_csh/{ps_single,sb_single}/` — committed reference
  output of the legacy csh `mt_prep_snap` pipeline against the synthetic
  fixtures. 20–21 artifacts per pass, covering every C++ binary's
  output. Regenerable via `bash tests/golden/capture.sh`.
- `tests/golden/_verify.py` — golden-tree classifier/comparator used by
  both `capture.sh --verify-only` and `test_golden_byte_identity.py`.
  Text + integer binaries must be byte-identical; float32 binaries are
  ulp-tolerant (rtol=1e-6) to absorb glibc last-bit drift across hosts.
- `tests/test_snaphu_build.py` — smoke-test that the vendored snaphu
  CMake wrapper downloads, patches, and builds a working snaphu binary.
- Auto-skip pytest markers (`linux_only`, `windows_only`, `requires_tcsh`)
  in `tests/conftest.py` so cross-platform CI doesn't need per-test
  `skipif` boilerplate.

### Changed
- `NOTICE` — corrected snaphu license statement from BSD-3-Clause to
  Stanford permissive + CS2 noncommercial (the embedded CS2 minimum-
  cost-flow solver is IG Systems and requires a separate commercial
  license).
- `external/snaphu/CMakeLists.txt` — drives snaphu's own Makefile via
  gcc/mingw32-make instead of attempting an MSVC build. The MSVC path
  is unreachable (snaphu uses POSIX `fork` + `getrusage`). Release
  workflow's MinGW job now builds snaphu and bundles `snaphu.exe` in
  the windows zip (previously missing).
- `tests/fixtures/generate_fixtures.py` — SB fixture now emits both
  master-named and pair-named `.rslc.par` inside each SMALL_BASELINES
  pair dir (upstream csh's `\\ls .../master.*slc.par` needs the former).
- PHASE: `PHASE_Preprocessing.mlapp` — removed dead-code `if isunix`
  inside `if ispc` download branch and reference to undefined
  `path_2_download_cmd`. Windows branch now uses `start "" /MIN cmd /c`
  uniformly.
- PHASE: `MatlabFunctions/STmodel_DET2D.m` — added missing `isunix/.bat`
  branch for geoSplinter invocation (the one DET/STC variant missed).

### Removed
- `external/snaphu/snaphu-msvc.patch` — the prior patch was fabricated
  (hunks did not match snaphu v2.0.6) and a full MSVC port is out of
  scope. Users on MSVC must supply a pre-built snaphu binary.

## [1.0.0] — <release date>

### Added
- Windows native support for SNAP preprocessor path (no WSL / Cygwin).
- CMake build system replacing Makefile (all platforms).
- Python 3.11 port of `mt_prep_snap` and `mt_extract_cands`.
- `matlab_compat/` helpers for cross-platform MATLAB shell-outs.
- Self-bootstrapping `.bat` shims with Microsoft Store stub detection.
- Golden-file test harness enforcing Linux/MinGW byte-identity.
- GitHub Actions CI matrix (Linux + macOS + Windows MSVC + Windows MinGW).
- SBOM + Sigstore attestation on release artifacts.

### Fixed
- `long magic` → `int32_t` — latent Linux LP64 garbage-read bug.
- GCC >= 10 strict-aliasing segfault in selpsc_patch / selsbc_patch.
- C-locale pinning in all C++ binaries (prevents German/Italian decimal-comma corruption).

## How to update this CHANGELOG

Each PR adds entries under `## [Unreleased]` with a subsection
(`### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Security`).
On tag push, Unreleased entries move to a new `## [x.y.z] — <date>` section.
