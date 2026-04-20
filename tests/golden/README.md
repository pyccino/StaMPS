# Golden outputs for legacy csh mt_prep_snap

`linux_csh/ps_single/` and `linux_csh/sb_single/` are the committed
reference outputs of the upstream csh `mt_prep_snap` pipeline driven
against the deterministic synthetic fixtures under
`tests/fixtures/synthetic_{ps,sb}/`. Two consumers:

- **`tests/test_golden_byte_identity.py`** — the Python mt_prep_snap
  port must produce a tree that matches these goldens (byte-identical
  for text/int artifacts, ulp-tolerant within rtol=1e-6 for float32
  binaries). Proves the port's logic matches the csh reference on the
  same host.

- **`.github/workflows/ci.yml :: linux-csh-baseline`** — every push
  re-runs the csh pipeline in CI and diffs against the committed
  tree. Catches non-determinism in either the pipeline or the C++
  binaries.

## File classification (enforced by `_verify.py`)

| Suffix family | Comparator | Why |
|---|---|---|
| `.txt`, `.in`, `.out`, `.list`, `.log`, `.base` | byte-identical | human-readable text; printf-bounded format |
| `.ij`, `.ij0`, `.ij.int` | byte-identical | integer pixel coordinates; no float math |
| `.flt`, `.da`, `.hgt`, `.ph`, `.ll` | float32 ulp-tolerant (rtol=1e-6) | output of libm-using C++ calamp/selpsc/pscphase/pscdem/psclonlat; last-bit drift across glibc versions is expected |

## Regenerating the tree

```bash
# From the StaMPS repo root on any Linux host with tcsh + gawk + cmake + gcc:
bash tests/golden/capture.sh
```

This:
1. Builds the C++ binaries via cmake (idempotent — skipped if `bin/calamp` is fresh)
2. Generates `tests/fixtures/synthetic_{ps,sb}/` if missing
3. Symlinks each fixture to `/tmp/stamps_golden_fixture/<pass>/` (canonical path so `.in` files embed a host-invariant prefix)
4. Runs the legacy csh `mt_prep_snap` under a shimmed `matlab` (noop)
5. Copies artifacts into `tests/golden/linux_csh/{ps_single,sb_single}/`

## Verifying without overwriting

```bash
bash tests/golden/capture.sh --verify-only
```

Runs the pipeline into a tmp dir and diffs against the committed tree
using `_verify.py`. Exit 0 iff all files match (tolerant). This is the
mode CI runs.

## When regeneration produces a diff

1. **Text/int mismatch** — real regression. Investigate before committing.
2. **Float-binary drift > 1 ulp** — real regression. Don't bump the
   goldens to "make the test pass" until you understand the root cause.
3. **Float-binary drift ≤ 1 ulp** — already absorbed by the tolerant
   comparator; no action needed.
4. **Trivial host change** (e.g., you updated the fixture generator) —
   regenerate with `capture.sh` (no args) and commit.

The `tests/golden/NONDET.md` file logs any "acceptable" non-determinism
cases with a justification — add a row there rather than silently
masking.
