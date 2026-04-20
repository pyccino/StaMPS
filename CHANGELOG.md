# Changelog

All notable changes to the StaMPS Windows port are documented here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

(entries added as PRs land)

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
