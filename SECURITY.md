# Security Policy

## Reporting vulnerabilities

Report security issues privately via GitHub's Private Vulnerability Reporting:
https://github.com/pyccino/StaMPS/security/advisories/new

Do NOT open public issues for security bugs. The fork maintainers respond
within 7 days.

## Supported versions

Only the most recent tagged release on `windows-port/main` is supported.
Older releases may contain unpatched dependencies (Triangle, snaphu).

## SLSA attestation

Every release includes a CycloneDX SBOM and Sigstore attestation. Verify:

    gh attestation verify <release-asset> --owner pyccino

Current SLSA target: SLSA Level 2 (provenance generated in CI, signed,
verifiable via Sigstore transparency log).
