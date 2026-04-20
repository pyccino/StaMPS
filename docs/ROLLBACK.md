# Rollback Procedure

If the Python port of mt_prep_snap or mt_extract_cands is producing
incorrect output on your system, you can revert to the original csh
implementation:

## Linux / macOS

Set the environment variable before invoking:

```bash
export STAMPS_LEGACY_CSH=1
mt_prep_snap 20200101 /data/my_stack 0.4
```

The shim at `bin/mt_prep_snap` detects the variable and delegates to
`bin/legacy-csh/mt_prep_snap` instead of the Python implementation.

## Windows

Legacy csh is not available on Windows (csh itself is not a native
Windows binary). If the Python port is failing on your Windows system,
please file an issue and use WSL as a temporary fallback.

## How to report a port bug

Set `STAMPS_LEGACY_CSH=1`, re-run, and attach both outputs to the issue:
- `~/legacy-output/` (csh)
- `~/python-output/` (Python port)

The outputs should be byte-identical. If they differ, that's the bug.
