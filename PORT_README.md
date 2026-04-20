# Windows Port Branch

This branch is the integration branch for the StaMPS native Windows port.
See `docs/superpowers/specs/2026-04-20-stamps-windows-port-design.md` and
`docs/superpowers/plans/2026-04-20-stamps-windows-port.md` in the parent
PHASE-StaMPS-rewrite project for design + implementation plan.

Upstream: https://github.com/dbekaert/StaMPS
Fork: https://github.com/pyccino/StaMPS (this fork)
Trunk for port work: `windows-port/main`
Phase-root branches: `windows-port/pr<N>` (no direct commits — PRs only)
Task branches (dash, never slash — git refs cannot nest a ref under
another existing ref, so `windows-port/pr1` and `windows-port/pr1/x`
cannot coexist):
  - `windows-port/pr<N>-<short-name>` for work under a phase root
    (example: `windows-port/pr1-rename-mt-prep`).
  - `windows-port/fix-<short-name>` for port follow-ups not tied to
    a numbered phase (example: `windows-port/fix-governance`).

The original `master` branch tracks upstream and is left untouched.
