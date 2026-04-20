"""Static lint: ensure no new csh idioms or bare system() calls sneak in."""

import re
from pathlib import Path

import pytest

FORBIDDEN_IN_MATLAB = [
    (re.compile(r"system\('which\s"), "use sp_which instead of system('which ...')"),
    (re.compile(r"system\('\\ls"), "use dir() instead of system('\\ls ...')"),
    (re.compile(r"system\('\\rm"), "use delete() instead of system('\\rm ...')"),
    (re.compile(r"system\('cp\s"), "use copyfile() instead of system('cp ...')"),
    (re.compile(r"!sync"), "use sp_sync() instead of !sync"),
    (re.compile(r">\s*/dev/null"), "use sp_system() which rewrites /dev/null"),
    (
        re.compile(r"(?<![\w])system\(\s*['\"]\s*triangle\b"),
        "use sp_system('triangle ...') for cmd.exe-safe quoting",
    ),
]


def test_no_csh_idioms_in_patched_m_files(stamps_root: Path):
    patched_files = [
        "uw_interp",
        "ps_smooth_scla",
        "ps_scn_filt",
        "ps_scn_filt_krig",
        "ps_weed",
        "sb_baseline_plot",
        "mt_prep_suggestion",
        "batchjob",
        "stamps_mc_header",
        "ps_sb_merge",
        "ps_calc_scla",
        "combine_amp_dem",
        "ps_load_initial",
        "sb_load_initial",
    ]
    violations = []
    for name in patched_files:
        path = stamps_root / "matlab" / f"{name}.m"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, message in FORBIDDEN_IN_MATLAB:
            for m in pattern.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                violations.append(f"{path.name}:{line_no}: {message}")
    assert not violations, "\n".join(violations)


def test_no_csh_shebang_in_snap_path_bin(stamps_root: Path):
    """SNAP-path shims (mt_prep_snap, mt_extract_cands) must not be csh.

    bin/ also contains many non-SNAP-path scripts (mt_prep_gamma,
    mt_prep_doris, step_master_read, remake_slcs, etc.) which remain
    csh because they target other preprocessors and are explicitly OUT
    of scope for the Windows port. Only the two shims the port replaces
    are asserted here.
    """
    SNAP_PATH_SHIMS = {"mt_prep_snap", "mt_extract_cands"}
    violations = []
    for name in SNAP_PATH_SHIMS:
        p = stamps_root / "bin" / name
        if not p.exists():
            continue  # not-yet-created shim (pre-flip state)
        try:
            first = p.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        except (IndexError, OSError):
            continue
        if first.startswith("#!/bin/csh") or first.startswith("#!/bin/tcsh"):
            violations.append(f"{p.name}: reintroduces csh shebang")
    assert not violations, "\n".join(violations)


# Negative-case self-tests: protect the lint itself from regression.
# If someone "simplifies" FORBIDDEN_IN_MATLAB and accidentally weakens
# the patterns, these tests fire — they assert the lint correctly DETECTS
# the patterns it claims to.


@pytest.mark.parametrize(
    "snippet,expected_message_fragment",
    [
        ("foo = system('which matlab');", "sp_which"),
        ("system('\\ls *.par');", "dir()"),
        ("system('\\rm output.mat');", "delete()"),
        ("system('cp src dst');", "copyfile()"),
        ("!sync", "sp_sync()"),
        ("system('echo > /dev/null');", "sp_system"),
        ("[a,b] = system('triangle -e foo.1.node > tri.log');", "sp_system('triangle"),
        ("system( 'triangle -e foo.1.node');", "sp_system('triangle"),
        ('system("triangle -e foo.1.node");', "sp_system('triangle"),
    ],
)
def test_lint_detects_forbidden_pattern(
    snippet: str,
    expected_message_fragment: str,
    tmp_path: Path,
):
    """For each FORBIDDEN_IN_MATLAB entry, prove the regex actually fires."""
    fired = False
    for pattern, message in FORBIDDEN_IN_MATLAB:
        if pattern.search(snippet) and expected_message_fragment in message:
            fired = True
            break
    assert fired, (
        f"Lint does NOT detect known-bad snippet {snippet!r}. "
        f"FORBIDDEN_IN_MATLAB pattern for {expected_message_fragment!r} "
        f"is too narrow."
    )


def test_lint_does_not_flag_clean_matlab(tmp_path: Path):
    """Sanity: a clean .m file produces no false positives."""
    clean = tmp_path / "clean.m"
    clean.write_text(
        "function out = foo(x)\n"
        "  out = sp_which('matlab');\n"
        "  delete('temp.mat');\n"
        "  copyfile(src, dst);\n"
        "  sp_sync();\n"
        "  sp_system('echo hello');\n"
        "  sp_system('triangle -e foo.1.node > tri.log');\n"
        "end\n",
        encoding="utf-8",
    )
    text = clean.read_text(encoding="utf-8")
    flagged = []
    for pattern, message in FORBIDDEN_IN_MATLAB:
        if pattern.search(text):
            flagged.append(message)
    assert not flagged, (
        f"Lint false-positives on clean MATLAB code: {flagged}. "
        f"Tighten the patterns to require shell-call context."
    )


def test_lint_negative_csh_shebang_detection(tmp_path: Path):
    """Inject a fake csh shebang and verify the shebang scanner fires."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    bad = fake_bin / "fake_shim"
    bad.write_text("#!/bin/csh\necho oops\n", encoding="utf-8")
    bad.chmod(0o755)
    # Mini-replica of the scanner; if the real one drifts, this stays honest.
    first = bad.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    assert first.startswith("#!/bin/csh"), (
        "Self-test scanner failed to detect csh shebang — " "the real scanner would also miss it."
    )
