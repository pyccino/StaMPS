# StaMPS Windows Port — __VERSION__

## Highlights

- (bullets curated by maintainer)

## Installation

Download `stamps-windows-x64-msvc.zip` (or `-mingw.zip`), verify
the SHA256 sum, and follow `INSTALL.md`.

```powershell
# One-liner install:
.\install-windows.ps1 -Repo pyccino/StaMPS-windows
```

## Verifying authenticity

```powershell
gh attestation verify stamps-windows-x64-msvc.zip --owner pyccino
# Also: compare SHA256 with SHA256SUMS-msvc asset
```

## Files

| Asset | Contents |
|---|---|
| `stamps-windows-x64-msvc.zip` | MSVC-built binaries + vendored external tools |
| `stamps-windows-x64-mingw.zip` | MinGW-w64 build (matches Linux byte-for-byte) |
| `stamps-src.tar.gz` | Full source (GPL v3 compliance) |
| `sbom.cdx.json` | CycloneDX SBOM |
| `SHA256SUMS-*`, `SHA512SUMS-*` | Checksums |

## Known limitations

- v1.0.0 binaries are unsigned; SmartScreen warns on first run ("More info → Run anyway"). v1.0.1+ ships SignPath-signed.
- Non-SNAP preprocessor paths remain Linux-only.

## Changelog

See `CHANGELOG.md`.
