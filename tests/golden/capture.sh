#!/usr/bin/env bash
#
# Capture golden outputs from the legacy csh mt_prep_snap pipeline.
#
# The committed goldens under tests/golden/linux_csh/{ps_single,sb_single}/
# serve as the byte-identity reference for the Python/MinGW/MSVC ports
# (AC3, AC4 in spec). This script is the source of truth for regenerating
# them — any non-determinism would surface here.
#
# Usage:
#   bash tests/golden/capture.sh                 # regenerate goldens
#   bash tests/golden/capture.sh --verify-only   # re-run + diff vs committed
#
# Requirements (CI has all of these via apt install tcsh gawk cmake):
#   - tcsh providing /bin/csh (Ubuntu's tcsh package creates this symlink)
#   - gawk
#   - cmake + gcc + make (to build C++ binaries)
#   - python3 (to generate fixtures)
#
# Why we shim matlab:
#   The upstream csh pipeline calls `matlab -nojvm < ps_parms_initial.m`
#   solely to seed parms.mat. Its output is MATLAB-internal and can't
#   byte-match across toolchains, so we shim it with /bin/true. The
#   ps_parms_initial.log file it produces is excluded from the golden
#   tree (see _exclude_patterns below).

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STAMPS=$(cd -- "$SCRIPT_DIR/../.." && pwd)
GOLDEN_ROOT="$SCRIPT_DIR/linux_csh"

VERIFY_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --verify-only) VERIFY_ONLY=1 ;;
        -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

for tool in tcsh gawk cmake make python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool '$tool' not on PATH" >&2
        exit 4
    fi
done
# Ubuntu's tcsh package creates /bin/csh; NixOS doesn't. If absent, we'll
# drive the legacy-csh scripts via `tcsh -f <script>` instead of relying on
# the shebang — handled in _capture_one below.
HAVE_BIN_CSH=0
[ -x /bin/csh ] && HAVE_BIN_CSH=1

# Build the C++ binaries (idempotent — skipped if already built).
if [ ! -x "$STAMPS/bin/calamp" ] || [ "$STAMPS/src/calamp.cpp" -nt "$STAMPS/bin/calamp" ]; then
    echo "==> building C++ binaries"
    cmake -S "$STAMPS/src" -B "$STAMPS/build" -DCMAKE_BUILD_TYPE=Release >/dev/null
    cmake --build "$STAMPS/build" --parallel >/dev/null
fi

# Generate deterministic synthetic fixtures.
if [ ! -f "$STAMPS/tests/fixtures/synthetic_ps/rslc/20200101.rslc" ]; then
    echo "==> generating fixtures"
    python3 "$STAMPS/tests/fixtures/generate_fixtures.py" >/dev/null
fi

# Work in a temp tree, then rsync into the golden dir at the end. Two passes
# (ps_single, sb_single) each drive legacy-csh/mt_prep_snap against the
# corresponding fixture.
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

# matlab shim (common to both passes).
mkdir -p "$TMP_ROOT/shims"
cat > "$TMP_ROOT/shims/matlab" <<'MATSHIM'
#!/bin/sh
# Swallow stdin + exit 0. ps_parms_initial.log stays empty; we exclude it.
cat >/dev/null
exit 0
MATSHIM
chmod +x "$TMP_ROOT/shims/matlab"

# On hosts without /bin/csh, shim mt_extract_cands to invoke the legacy-csh
# version via `tcsh -f` (bypassing the script's #!/bin/csh shebang). With
# STAMPS_LEGACY_CSH=1 the committed bin/mt_extract_cands sh shim would
# exec the legacy-csh script — but that fails at the shebang on NixOS.
if [ "$HAVE_BIN_CSH" -eq 0 ]; then
    cat > "$TMP_ROOT/shims/mt_extract_cands" <<EOF
#!/bin/sh
exec tcsh -f "$STAMPS/bin/legacy-csh/mt_extract_cands" "\$@"
EOF
    chmod +x "$TMP_ROOT/shims/mt_extract_cands"
fi

# Files that must NEVER enter the golden tree because they contain
# toolchain-specific or run-specific bits (matlab stub output, PATH-derived
# sentinels). Matched by basename (not path) for simplicity.
_exclude_basenames=(
    "ps_parms_initial.log"
    "sb_parms_initial.log"
)

_is_excluded() {
    local name="$1"
    for e in "${_exclude_basenames[@]}"; do
        [ "$name" = "$e" ] && return 0
    done
    return 1
}

# Canonical fixture path used BOTH during capture and later during
# byte-identity verification. The .in files written by calamp / selpsc
# embed this path literally, so it must match across hosts where the
# golden tree is diffed. /tmp/<fixed>_ps works on Linux/macOS; Windows
# hosts can set STAMPS_GOLDEN_FIXTURE_ROOT to override.
GOLDEN_FIXTURE_ROOT="${STAMPS_GOLDEN_FIXTURE_ROOT:-/tmp/stamps_golden_fixture}"

# One capture pass. Args: pass_name fixture_path da_thresh.
#
# Why not a relative symlink inside workdir: mt_extract_cands cd's into
# each PATCH_N subdir and invokes selpsc_patch with paths taken from
# $WORKDIR/selpsc.in. Those paths are resolved relative to cwd (the
# PATCH dir), so a relative `fixture/` in the top workdir is unreachable
# from the child. An absolute canonical path sidesteps the subdir
# traversal entirely and stays byte-stable across hosts because we pick
# a fixed tmp path.
_capture_one() {
    local pass="$1" fixture="$2" da="$3"
    local workdir="$TMP_ROOT/$pass"
    mkdir -p "$workdir"

    local canon="$GOLDEN_FIXTURE_ROOT/$pass"
    rm -rf "$canon"
    mkdir -p "$(dirname "$canon")"
    ln -s "$fixture" "$canon"

    cd "$workdir"

    STAMPS="$STAMPS" STAMPS_LEGACY_CSH=1 \
        PATH="$TMP_ROOT/shims:$STAMPS/bin:$PATH" \
        LC_ALL=C \
        tcsh -f "$STAMPS/bin/legacy-csh/mt_prep_snap" \
            20200101 "$canon" "$da" 1 1 50 50 \
            >"$workdir/_capture.stdout" 2>&1 || {
                echo "FAIL: $pass capture produced nonzero rc" >&2
                cat "$workdir/_capture.stdout" >&2
                exit 5
            }
    # _capture.stdout is a run-log, not a golden artifact.
    rm -f "$workdir/_capture.stdout"
}

_capture_one ps_single "$STAMPS/tests/fixtures/synthetic_ps" 0.4

# TODO: sb_single capture blocked on fixture naming mismatch.
# The legacy csh's SB detection does:
#   \ls $datadir/SMALL_BASELINES/*/$master.*slc.par
# expecting MASTER-named .par files (e.g. 20200101.rslc.par) inside each
# pair dir. Our synthetic_sb generator writes PAIR-named .par files
# (20200101_20200113.rslc.par) which don't match that glob, so tcsh
# hangs. Fix: either update generate_fixtures.py to emit master-named
# par files (and update the SHA256 manifest), or add a csh-compatible
# symlink layer in capture.sh. Tracking as follow-up.
# _capture_one sb_single "$STAMPS/tests/fixtures/synthetic_sb" 0.6

# Filter out excluded files before committing (or comparing).
_prune_excludes() {
    local root="$1"
    for e in "${_exclude_basenames[@]}"; do
        find "$root" -name "$e" -type f -delete 2>/dev/null || true
    done
}
_prune_excludes "$TMP_ROOT/ps_single"

if [ "$VERIFY_ONLY" -eq 1 ]; then
    echo "==> verifying against committed goldens"
    rc=0
    for pass in ps_single; do
        if [ ! -d "$GOLDEN_ROOT/$pass" ]; then
            echo "MISSING: $GOLDEN_ROOT/$pass (not yet committed)"
            rc=1
            continue
        fi
        if ! diff -r "$GOLDEN_ROOT/$pass" "$TMP_ROOT/$pass"; then
            echo "MISMATCH in $pass"
            rc=1
        fi
    done
    exit "$rc"
fi

# Capture mode: copy into the committed tree.
echo "==> installing goldens"
mkdir -p "$GOLDEN_ROOT"
for pass in ps_single; do
    rm -rf "$GOLDEN_ROOT/$pass"
    cp -r "$TMP_ROOT/$pass" "$GOLDEN_ROOT/$pass"
done
echo "==> done. artifacts under $GOLDEN_ROOT/"
ls "$GOLDEN_ROOT"/ps_single | head -5
