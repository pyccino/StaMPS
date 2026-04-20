# SignPath OSS Status

**Application submitted:** 2026-04-20 (PENDING — owner must complete)
**Status:** AWAITING APPROVAL (typical: 1–2 weeks)
**Tracker:** https://signpath.io/signpath-foundation/

## When approval lands — REQUIRED FOLLOW-UPS

1. Add SignPath secrets on the fork:
   - `gh secret set SIGNPATH_API_TOKEN < <(read -s)`
   - `gh secret set SIGNPATH_ORG_ID -b "<from-signpath-dashboard>"`
   - `gh secret set SIGNPATH_PROJECT_SLUG -b "stamps-windows"`
2. Add a SignPath signing step to `.github/workflows/release.yml` in the
   `build-msvc` job, BEFORE the `Package` step. Use the action:
   ```yaml
   - uses: signpath/github-action-submit-signing-request@<sha>  # pin
     with:
       api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
       organization-id: ${{ secrets.SIGNPATH_ORG_ID }}
       project-slug: ${{ secrets.SIGNPATH_PROJECT_SLUG }}
       artifact-configuration-slug: stamps-binaries
       signing-policy-slug: release-signing
       wait-for-completion: true
   ```
3. Cut a `v1.0.1` release with the signed binaries.
4. Update `INSTALL.md` SmartScreen section: "v1.0.1+ ships SignPath-signed."
5. Update `CHANGELOG.md` `[Unreleased] → Added` entry.
6. Delete `docs/SIGNPATH_STATUS.md` and remove the open issue tag.

## Re-enable issue tracking

A GitHub issue is opened with title "Re-enable SignPath signing" and label
`signpath-pending`. Close it as part of step 6 above.

## Why this file exists

SignPath approval is asynchronous and easy to forget. This file is a hard
checkpoint: when CI sees `docs/SIGNPATH_STATUS.md` AND a release is being
cut, the workflow prints a reminder banner. See `.github/workflows/release.yml`
step `signpath-reminder` (added by Task 4.4).
