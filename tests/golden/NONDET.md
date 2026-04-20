# Non-Deterministic Output Files

Files listed here differ across three consecutive runs of the csh
`mt_prep_snap` on the reference host during golden capture. Each entry must
justify why the difference is acceptable.

## Cases discovered

(none yet — populated during Task 2c.2)

## Normalization rules applied

See `tests/_normalize.py`.

## If this file grows beyond ~10 entries

That's a sign we have non-determinism in our own code, not just environment
noise. Treat it as a bug.
