# Developing the StaMPS Windows Port

This guide is for contributors to the `phase-team/StaMPS-windows` fork.
For users, see `INSTALL.md`.

## Build from source — all 4 platforms

### Linux (GCC 13 on Ubuntu 22.04+)

    sudo apt install -y cmake tcsh gawk python3.11 python3-pip
    cmake -S src -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build
    cmake --install build
    pip install -e .[test]
    python -m pytest tests/ -v

### macOS (Xcode Command-Line Tools, Homebrew)

    brew install cmake
    cmake -S src -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build
    pip install -e .[test]
    python -m pytest tests/ -v

### Windows MSVC (Visual Studio 2022 Build Tools)

    cmake -S src -B build -G "Visual Studio 17 2022" -A x64
    cmake --build build --config Release
    pip install -e .[test]
    python -m pytest tests/ -v

### Windows MinGW-w64 (MSYS2)

    pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
    cmake -S src -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
    cmake --build build

## Running tests locally

    python -m pytest tests/ -v                    # all Python tests
    python -m pytest tests/ -v -m "not nightly"   # skip slow E2E
    python -m pytest tests/ -v -m "linux_only"    # Linux-only subset
    matlab -batch "addpath('matlab_compat'); runtests('tests/matlab')"

## Adding a patched `.m` file

1. Identify the Unix-ism (`system()`, `!cmd`, `>& /dev/null`, `\\ls`, etc.).
2. Add the edit to the 15-row table in Plan §3.7-3.21 with line number + OLD/NEW.
3. Write a concrete test method in `tests/matlab/test_matlab_patches.m` — no
   `assumeTrue(false, 'Placeholder')` left behind.
4. Run `matlab -batch "addpath('matlab_compat'); runtests('tests/matlab/test_matlab_patches.m')"`.
5. Verify `tests/test_lint_no_csh.py` still passes.
6. Open a PR.

## Golden regeneration

When `bin/mt_prep_snap` or `bin/mt_extract_cands` csh sources change intentionally:

1. Run `bash tests/golden/capture.sh` on a Linux host with tcsh installed.
2. Inspect the diff vs. prior golden: `git diff tests/golden/`.
3. Open a PR titled `goldens: refresh for <reason>`.
4. Two reviewers approve: one domain, one CI.

## Running CI locally via `act`

`act` runs GitHub Actions workflows locally in Docker. Useful for CI debugging.

    # Linux job:
    act -j build-linux
    # Windows jobs: NOT SUPPORTED by act (Windows containers require paid Docker Desktop)

⚠️ **Warning:** Never run `act` against a PR from an untrusted contributor.
`act` executes workflow steps as your host user; a malicious workflow can
exfiltrate your SSH keys, AWS creds, etc. Only run `act` on code you've
read in full.

## Pre-commit hooks

Install pre-commit (see Task 4.12):

    pip install pre-commit
    pre-commit install

Hooks enforce: ruff format, ruff check, mypy on `python/stamps/`, trailing
whitespace, no CRLF in source files, no SHA256 placeholders in external/.

## Branching and Worktrees

The port uses a strictly linear branch hierarchy. All refs live under
`windows-port/` on the fork (`pyccino/StaMPS`); the original `master`
branch tracks upstream `dbekaert/StaMPS` and is left untouched.

### Branch naming

- **Integration trunk:** `windows-port/main`. All phase work eventually
  lands here via PR. Only the orchestrator merges to trunk (see
  `PORT_README.md` for ownership rules).
- **Phase-root branches:** `windows-port/pr<N>` (e.g. `windows-port/pr1`,
  `windows-port/pr2`). Use a dash, never a slash, between `pr` and the
  number. No direct commits — PRs only.
- **Task branches under a phase root:**
  `windows-port/pr<N>-<short-name>` (example:
  `windows-port/pr1-rename-mt-prep`).
- **Port follow-up fixes** not tied to a numbered phase:
  `windows-port/fix-<short-name>` (example:
  `windows-port/fix-governance`).

**Why dash, not slash:** git refs cannot collide in hierarchy. A branch
named `windows-port/pr1` prevents creation of `windows-port/pr1/rename`
(and vice-versa) because git stores refs as filesystem paths under
`.git/refs/heads/` — a file and a directory cannot share a name. Use
dashes consistently to avoid the collision entirely.

### Worktree convention

Each task lives in its own git worktree so that unrelated work cannot
cross-contaminate. The parent project layout is:

    Phase-StaMPS-rewrite/
    ├── StaMPS/                    # primary checkout of windows-port/main
    └── worktrees/
        ├── <task-name>/           # one worktree per task
        └── ...

Create a worktree for new task work with:

    cd Phase-StaMPS-rewrite/StaMPS
    git worktree add -b windows-port/pr<N>-<task> \
        ../worktrees/<task-name> windows-port/pr<N>

Remove it after the PR merges:

    git worktree remove ../worktrees/<task-name>
    git branch -d windows-port/pr<N>-<task>

### Ownership and merging

See `PORT_README.md` for the full ownership matrix. In short: workers
push task branches and open PRs; only the orchestrator merges to phase
roots and to `windows-port/main`.

## Release process

1. All PRs merged to `windows-port/main`.
2. CI green on all 5 jobs (incl. Italian-locale canary).
3. Maintainer bumps `CHANGELOG.md` from `[Unreleased]` to `[X.Y.Z]`.
4. Maintainer commits + signs tag: `git tag -s vX.Y.Z -m "Release vX.Y.Z"`.
5. Push tag: `git push fork vX.Y.Z`. Release workflow auto-runs.
6. Verify release assets on GitHub Releases page.
7. Verify Sigstore attestation: `gh attestation verify <asset> --owner pyccino`.

## Contacting maintainers

See MAINTAINERS.md.
