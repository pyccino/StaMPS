# Non-Deterministic Output Files

Files listed here differ across three consecutive runs of the csh
`mt_prep_snap` on the reference host during golden capture. Each entry must
justify why the difference is acceptable.

## Cases discovered

Golden capture ran twice on Linux GCC 13 + glibc 2.39 + tcsh 6.24.00 (Ubuntu
24.04 runner — the image `ubuntu-latest` pointed at on 2026-04-20, when the
`linux-csh-baseline` CI job captured the goldens); all outputs were
byte-identical between runs. Known cross-platform drift: last-bit
libm differences on MSVC and macOS libsystem_m (documented in
`test_generate_fixtures.py` lines 88-96) — enforced via ulp-tolerant comparison
in `_verify.py` (rtol=1e-6).

## Normalization rules applied

See `tests/_normalize.py`.

## If this file grows beyond ~10 entries

That's a sign we have non-determinism in our own code, not just environment
noise. Treat it as a bug.
