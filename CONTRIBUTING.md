# Contributing to StaMPS Windows Port

## Quick start

1. Fork `pyccino/StaMPS` on GitHub.
2. Clone and configure:
   ```
   git clone https://github.com/<your-fork>/StaMPS.git
   cd StaMPS
   git remote add upstream https://github.com/pyccino/StaMPS.git
   git checkout windows-port/main
   ```
3. Create a branch: `git checkout -b windows-port/feature/<short-name>`.
4. Follow the TDD discipline in `docs/superpowers/plans/...`.
5. Signed commits required: `git config --global commit.gpgsign true`.

## Commit style

Conventional Commits:
- `feat:` new feature
- `fix:` bug fix
- `test:` test addition/fix
- `docs:` documentation
- `build:` build-system change
- `ci:` CI change
- `chore:` chore

Each TDD cycle is one commit.

## Running tests locally

```
pip install -e .[test]
python -m pytest tests/ -v
```

For MATLAB tests:
```
matlab -batch "addpath('matlab_compat'); runtests('tests/matlab')"
```

For golden regeneration (Linux only):
```
bash tests/golden/capture.sh
```

## Branch naming

- `windows-port/main` — integration trunk.
- `windows-port/pr<N>` — phase-root branches (no direct commits; PRs only).
- `windows-port/feature/<name>` — individual feature work.

## PR checklist

- [ ] Commit is signed.
- [ ] CI is green on all 5 OS/compiler jobs.
- [ ] New behavior has a test.
- [ ] `CHANGELOG.md` Unreleased section updated.
- [ ] If adding a MATLAB patch: also add a test method to
      `tests/matlab/test_matlab_patches.m`.
- [ ] If adding a C++ binary: also add its CTest smoke in `src/CMakeLists.txt`.

## Golden-file updates

If your change modifies csh `mt_prep_snap`/`mt_extract_cands` output
(intentionally), regenerate goldens per `tests/golden/REGEN.md`. PR title
must start with `goldens:` and requires two approvers.

## Upstream submission

After features land in `windows-port/main` and ship as a release, we
opportunistically submit PRs to `dbekaert/StaMPS`. Don't block on
upstream acceptance — the fork is the primary artifact for PHASE users.
