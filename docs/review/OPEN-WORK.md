# Open work

## Current checkpoint: 1 October 2026

Packet P, on main after PR122 (roadmap docs). Facebook 580 kept failing at Patch apk because
`De-Vanced Settings` depends on `AMOLED dark theme`, whose `FdsContextColor580Fingerprint`
does not match the APK. Packet P drops `De-Vanced Settings`; see the 1 October update in the
[decision record](FACEBOOK-580-2026-09-29.md). Prime Video 3.0.470.357 is built and published
(not phone-tested), and the Nightly watch is green again (30 Sep).

Still open: the first green Facebook build (then #105), the YouTube failure in #114, the Edge
apkpure refusal, provider watch #102, F05/F06, owner confirmation of YouTube's two new patch
names (Playback buffer, Restore original titles) and the older items below. Lanes and parked
ideas live in [the roadmap](../../knowledge/ROADMAP.md).

## Previous checkpoint: 29 September 2026

Packet L, one PR on main `93fc2b98`. What it fixes, with the evidence in the PR body:

- **Poll rebuilds:** a pinned target is triggered only by its pinned provider; hoo-dles
  prereleases had rebuilt the rushiranpise-pinned AdGuard four times on 28 Sep with identical
  inputs. Poll-only runs resolve only the targets Build will consume; the first cron and manual
  runs still observe all of them, and unobserved targets stay UNKNOWN in the report.
- **Resolver reasons:** a failed shadow resolution prints this repo's own fixed reason plus
  allowlisted `resolve.sh` summary lines, never upstream text.
- **Prime Video:** `lib/arm64-v8a/libInit.so` is an 11-byte `release=NNN` marker (452, now 470).
  Exactly that whole-member shape, byte-identical to the patcher input, is accepted as data.
- **Facebook:** moved to 580.0.0.51.74 with four owner-chosen patches; see the
  [decision record](FACEBOOK-580-2026-09-29.md).
- **Nightly Watch:** names are checked against the exact channel-selected bundle of every
  candidate and extra (GitHub and GitLab) with `src/etc/selection_names.py`; the release read
  is authenticated. Version, option and default comparison remain open. The check lists
  universal patches too; the provider watch baselines were recorded with `-x -u`, which omits
  them, so watch deltas (#102) are blind to universal-patch changes.
- **Council j4:** uncited votes are dropped, busy or unreachable models fall through, and a
  factual `ask` mode answers from cited fact keys. See [the council README](../council/README.md).

- **Shadow source reasons:** Edge's shadow source preparation has failed every run since at
  least 28 Sep while its real builds publish (last 21 Sep, 223.4 MB). The job log holds only a
  fixed warning because `source_inputs.py` swallowed the reason; it now prints its own reason,
  the fetcher's exit code and duration, and the observed manifest facts.

First post-merge run (36534562050, see the [session record](SESSION-2026-09-29.md)): Prime
Video built 3.0.470.357 and AdGuard ignored the other provider, as intended. Facebook 580 failed
at patch time on an AMOLED theme fingerprint pulled in as a dependency; nothing was published.

Still open: the Facebook dependency failure, the Edge reason line in that run's log, closing
#98/#101/#104 with the Prime evidence, #105 after Facebook builds, #99 after the next Nightly,
full F05/F06 fingerprints, provider watch #102 (blind to universal patches), PR53, and the
older items below. Prime Video is built, not phone-tested.

## Earlier checkpoint: 27 September 2026

Main after PR89 (`2f3acecd`) plus the 5S hygiene packet. Start with the
[review desk](README.md), then the [5S audit](AUDIT-5S-2026-09-27.md). Next
engineering packet: F05/F06, covering every build input (tools, runtime, patch
defaults) and a durable record of the last fully successful publication, still
shadow-only. The 26 September section below is now the previous checkpoint.

## Latest checkpoint: 26 September 2026

Start with the [26 September handover](HANDOVER-2026-09-26.md): current main after
PR86-PR88, the five exact-version source fallbacks (Photos with its exact signer
rotation pair), workflow schedules in IST, the release and branch cleanup record
and the next entry point. Dated sections below are history, not current state.

## Verified checkpoint: 23 September 2026

[PR75](https://github.com/govinda-rajulu/patch-factory/pull/75) merged as
`e1711ebc936f44a6f227106818df47256ff4c5cc`, tree
`d21c35964ca7df2a2da883bdb42702498d53fd65`; main validation
[35696640034](https://github.com/govinda-rajulu/patch-factory/actions/runs/35696640034)
passed. Scheduled Daily
[35758471077](https://github.com/govinda-rajulu/patch-factory/actions/runs/35758471077)
later succeeded on the same commit, with 14 shadow dependency observations and
real Reddit, YouTube, Prime Video, Hotstar and AdGuard publications. New APK
bodies were not independently downloaded, and this does not prove the earlier
Reddit failure cause. This is a dated evidence checkpoint, not a permanent
claim about the current branch.

## Before a fresh all-target publication

- **Exact-version source fallbacks (26 Sep 2026):** 4 admissions (reddit, telegram, facebook, truecaller-combo) act only after the primary download fails for that exact version. Photos 7.92.0.977185651 is
  admitted separately with an exact v3.0->v3.1 signer rotation pin. See the
  [admission record](APK-SOURCE-ADMISSIONS-2026-09-26.md) and the
  [Photos rotation record](APK-SOURCE-ADMISSION-PHOTOS-2026-09-26.md).
- **Reddit later recovered by schedule:** Daily35758471077 published Reddit
  2026.38.0 with the finished-identity, handoff and release stages successful.
  Earlier run35637130545 remains a historical failed attempt; the exact root
  cause is unproven. Publication receipts and host digests exist, but their new
  bodies were not downloaded in this review and device behavior is untested.
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
7. **Reconciliation and cleanup:** targeted agent guidance/skills and issue
   evidence still need review. The old 39-release/43-asset cleanup preview is
   stale after the 86-release inventory and has no APK-byte recovery backup.
   Historical issue corrections are not posted or closed merely because
   repository documentation changes. PR53 disposition needs its own current
   inspection, not automatic closure.
8. **Remaining UI request:** official app logos need provenance/usage review.
   Font/navigation icons are shipped; neither equals official app artwork.
9. **Upstream attribution/provenance:** FiorenMas upstream was reviewed at
   commit `733e91b6fe90dace2295ac6a27ca66481c945e7d` on 23 September 2026.
   Its PR168 churn, mutable release tag, public signing material and broad CI
   permissions are warnings, not components to copy. Morphe NOTICE handling
   and per-provider pinned license/source records still need periodic review.

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
