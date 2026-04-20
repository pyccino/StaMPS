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

## Key rotation and revocation

If the SignPath API token is compromised (leaked credential, suspected
exfiltration from CI logs, departing maintainer, etc.), treat it as an
incident and follow these steps in order:

1. **Revoke immediately** via the SignPath dashboard
   (https://app.signpath.io/ → *API Tokens* → *Revoke*). Do this FIRST,
   before any other step — a live token is actively signing.
2. **Generate a new token** in the SignPath dashboard with the minimum
   scope required by the release workflow.
3. **Update the GitHub secret** on the fork:

        gh secret set SIGNPATH_API_TOKEN --repo pyccino/StaMPS < <(read -s)

   (Paste the new token at the `read -s` prompt; it will not echo.)
   Also update any environment-scoped copies if the release job uses a
   GitHub Environment gate.
4. **Re-run the most recent release workflow** so any artifacts that
   were pending signature when the token was revoked get re-signed with
   the new token:

        gh run rerun --repo pyccino/StaMPS <run-id>

   Do NOT manually delete unsigned artifacts from the release — the
   workflow replaces them atomically on success.
5. **Notify downstream** via the advisory channel documented in
   `SECURITY.md` (GitHub Security Advisory + release-notes call-out).
   If signed artifacts were produced with the compromised token,
   the advisory MUST name the affected version range so that
   verifiers re-check signatures against the new public key.

## Why this file exists

SignPath approval is asynchronous and easy to forget. This file is a hard
checkpoint: when CI sees `docs/SIGNPATH_STATUS.md` AND a release is being
cut, the workflow prints a reminder banner. See `.github/workflows/release.yml`
step `signpath-reminder` (added by Task 4.4).
