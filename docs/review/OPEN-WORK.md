# Open work

## Verified checkpoint: 19 September 2026

[PR67](https://github.com/govinda-rajulu/patch-factory/pull/67) merged as
`d2777e30d4e06c8f28a1e4cfe600d1309344b865`, tree
`efb2797ba0f29983596fd48b5b68edfda1166441`.
[Main validation](https://github.com/govinda-rajulu/patch-factory/actions/runs/35456210369)
and [Pages](https://github.com/govinda-rajulu/patch-factory/actions/runs/35456209682)
passed on that commit. This is a dated evidence checkpoint, not a permanent
claim about the current branch.

## Before a fresh all-target publication

- **Reddit exact-version source:** the
  [page-only probe](https://github.com/govinda-rajulu/patch-factory/actions/runs/35456286555)
  observed HTTP 200 for both requests. The 2026.38.0 request had no download
  anchor and resolved outside the expected package path; the current-download
  page had one anchor and retained the package path. No APK was transferred.
  This does not prove historical cause or recovery. Verify the exact supported
  version's source/identity before changing a downloader or choosing a fallback.
- **Six resource-reduction selections excluded:** APK Junk Cleanup, Remove Duplicate
  Graphics and Remove Languages in each of `esfile-ftl` and `mxplayer-ftl`.
  Following the owner's delegated reliability review, they are removed from
  includes and explicitly excluded in their own bundle. This is not approval
  to apply them and does not change historical APKs. See the
  [resource decision](RESOURCE-DECISION-2026-09-19.md) for rationale and limits.
- **Campaign authorization and inventory:** explicit targets, publication intent,
  exact source commit and duplicate-run checks before dispatch. The Batch
  workflow can publish successful targets even when another target fails.
  A failed target retains its prior working download.
- **Recovery and cleanup:** independently recoverable copies before destructive
  cleanup; exact fresh release/asset preview and explicit approval afterward.
  No release deletion, signing restore or phone installation is authorized by
  this file.

## Shipped, with limits

- PR41-47: requested/applied and output gates, transport checks, preview-only
  retention, unique build identities and the exact YouTube exclusion.
- PR48 separation and PR51-59: useful planning/validation/notifier/shadow work
  merged; the failed mandatory-session experiment is not a current prerequisite.
- PR60/61: optional MicroG, neutral catalog and unified imports, filters,
  self-hosted font/navigation icons, prepared dependency reuse and qualification
  groundwork. MicroG is not a fifteenth patched target.
- PR62/63: action compatibility repair, mandatory runtime smoke, grouped
  minor/patch Dependabot updates, visitor-first release notes and inline reports.
  No automatic merge or blanket compatibility guarantee.
- PR64: prepared dependency subset comparison for all configured targets and a
  read-only report. This is shadow-only, not full fingerprints or build selection.
- PR66/67: scoped store logging/missing-link diagnostics, visible MicroG channel
  selection and mixed-run reporting. Reddit recovery is not established.

## Core engineering still open or partial

1. **Full fingerprints and durable baselines:** pre-resolve exact source APK and
   remaining runtime/OS/transitive/effective-default inputs; consume those exact
   files; observe every enabled target, including legacy-omitted ones. Preserve
   the original semantic poller controls, not just a new test count. Missing or
   legacy evidence is UNKNOWN. No scheduling/skip authority from partial hashes.
2. **Qualification trust:** current qualification requires a successful whole
   source workflow. A published app from a mixed red run is not automatically
   qualified. Per-target qualification would be a separate policy change;
   independent provenance/attestation and reproducibility remain unfinished.
3. **Watcher decisions:** complete expected-versus-checked provider/extra/default
   coverage, trustworthy changes and actionable options on the existing site.
   Inline issue text and green workflows are not complete evidence.
4. **Same-version Obtainium delivery:** APPVERSION-only extraction does not
   guarantee notification for patch-only rebuilds. Existing tracking migration
   and Android behavior require separate consent and tests; no catalog autosync.
5. **Governance and onboarding:** required-CI/bypass inspection, shared add-target
   schema and disabled semantics, GitLab-primary capability and effective/default
   patch approvals. Do not infer settings enforcement from a CODEOWNERS file.
6. **Supply chain and recovery:** independent original-APK trust, reviewed
   alternative-source pilot, narrower fetch/patch/sign boundaries, container
   update review, fresh restore-tested repository/assets backup, signing restore
   and phone validation. Do not make an unrelated MX verifier retry a prerequisite.
7. **Reconciliation:** targeted agent guidance/skills and issue evidence still
   need review. Historical issue corrections are not posted or closed merely
   because repository documentation changes. PR53 disposition needs its own
   current inspection, not automatic closure.
8. **Remaining UI request:** official app logos need provenance/usage review.
   Font/navigation icons are shipped; neither equals official app artwork.

## Owner decisions to preserve

Keep the generated enabled-target inventory, the frozen `truecaller-v26.10.6`
release and the attic. SonyLIV/ZEE5 remain retired; do not invent a shared reason
or reactivate them. The patcher intentionally moves with validated latest stable.
Provider age is advisory. Preserve channels, pins, ceilings and per-bundle
selection semantics unless separately reviewed.

Keep YouTube's exact exclusion `Remember live stream playback position` and the
approved GmsCore support, PoToken provider and Spoof video streams dependencies.
The older differently spelled review-sheet entry does not override that decision.
Remove Debug Info is quarantined, not established upstream-fixed.

Optional Reddit Morphe, ES File/rushiranpise, Photos/RookieEnough and
Instagram/Stylus remain candidates for review, not approved configuration changes.
Patch-name presence is not proof of compatibility or collision-free composition.

## Keeping this page useful

Update evidence links and mark shipped/partial/blocked/deferred explicitly.
Generated target data belongs in README's state block, not another hand-maintained
inventory. Never publish private backup details, signing information or chat
exports to make a handover look complete. Preparation, approval, local tests,
CI, publication and phone tests are separate states.
