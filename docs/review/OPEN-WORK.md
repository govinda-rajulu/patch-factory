# Open work

## Current checkpoint: 9 October 2026, evening (packet W7)

W7 (one pull request on top of W6 #163): version step-down for apps above the phone cap,
any-version providers take the store's newest, Amazon Music and LinkedIn unpinned, short MicroG
card, `docs/status.html` deleted, launcher rule in the STATE opening message. Record:
[SESSION-2026-10-09.md](SESSION-2026-10-09.md) (W7 section). Open, in order:

1. Owner runs the W7 controller (merges #163 and W7, builds Amazon Music and LinkedIn) and
 uploads its RESULT file. Phone-test both (Amazon on a throwaway account only); if Amazon will
 not install, add `Rename shared permissions`.
2. Noise pass from the RESULT inventory: stale open issues, open pull requests, leftover
 branches, schedules, release counts, cleanup preview.
3. Retire the old `release_retention.py` preview in the release action (two retention policies print side by side). Store step-down for APKPure-source apps (W7 steps down on APKMirror listings and provider
 lists only).
4. Onboarding review gpt seat parser (needs a failing log); openskip handbook copy of the
 W5 to W7 lessons by its own PR.
5. Then the W4 list below (#102, council `same_site`, free seats, release notes, S2, ...).

## Earlier checkpoint: 9 October 2026, afternoon (packet W6)

Done since W5 outside pull requests: W5 merged (#162); LinkedIn built (run 37912428867);
cleanup applied a second time (22 releases, 22 tags; receipt
`~/work/run-logs/cleanup-receipt-20261009T091933Z.json` on the owner box). W6 (one pull
request): Amazon Music's `libInit.so` version marker (`4.6.14`) accepted by the native check,
build workflows keyed by app on the status data and Pages. Record:
[SESSION-2026-10-09.md](SESSION-2026-10-09.md). Open, in order:

1. Merge W6. Run `1. Manual Patch` for `amazonmusic`. If it stops at a new check, paste the
 reason line. Phone-test both apps (Amazon on a throwaway account only); if Amazon will not
 install, add `Rename shared permissions`.
2. "Any"-version providers (Amazon Music): follow the store's newest Android 10 version
 automatically instead of a hand-raised `max_app_version` (joins S2 version step-down).
3. Onboarding review gpt seat sometimes returns invalid finding fields; needs the failing
 run's log before a parser change.
4. Copy the W5 and W6 lessons (knowledge/LESSONS.md, 9 Oct) to openskip's handbook by its own PR.
5. Then the W4 list below (#102, council `same_site`, free seats, release notes, S2, ...).

## Earlier checkpoint: 9 October 2026 (packet W5, session close)

Done on 8 to 9 Oct outside pull requests: cleanup applied (4 releases, 96 tags; receipt
`~/work/run-logs/cleanup-receipt-20261009.json` on the owner box); 18 merged branches archived
(`~/work/pf-archive/patch-factory-branches-20261008T215522Z.bundle`, INDEX line) and deleted.
W5 (one pull request): LinkedIn pinned to 4.1.1255.1, Amazon Music pinned to 26.34.0, cleanup
keeps only each app's two newest builds, disabling an app passes the suite. Open, in order:

1. Merge W5. Run `1. Manual Patch` for `linkedin` and `amazonmusic`; phone-test both (Amazon on
 a throwaway account only). LinkedIn still "needs SDK": disable it (`5. Add target`, disable).
 Amazon will not install: add `Rename shared permissions`.
2. Cleanup: run the W5 controller's printed apply command (token changes with every nightly run;
 a stale token stops with nothing deleted and prints the new one).
3. "Any"-version providers (Amazon Music): follow the store's newest Android 10 version
 automatically instead of a hand-raised `max_app_version` (joins S2 version step-down).
4. Status: a Manual Patch failure of one app marks the whole workflow red until any later
 Manual Patch works; consider keying build workflows by app only.
5. Onboarding review gpt seat sometimes returns invalid finding fields; check its parser.
6. Copy the W5 lessons (knowledge/LESSONS.md, 9 Oct) to openskip's handbook by its own PR.
7. Then the W4 list below (#102, council `same_site`, free seats, release notes, S2, ...).

## Earlier checkpoint: 8 October 2026, afternoon (packet W4)

W4 (one pull request): Pages Builds and Watch rebuilt on `status.json`, failures listed until
fixed, MicroG RE six-file card, Obtainium import with icon choice, Amazon Music and LinkedIn,
a working two-step app add, cleanup tool, obsolete files removed. Record:
[SESSION-2026-10-08.md](SESSION-2026-10-08.md) (W4 section). Open, in order:

1. Merge W4 (#160). Its onboarding review blocks Amazon Music's "Unlock Unlimited" and
 "Unlimited track skipping" under rule 1; the owner keeps them for a throwaway-account test
 and merges over that block (record: `onboarding/amazonmusic.md`). Run `Status page data`;
 open the page. The review's gpt seat answered with invalid finding fields; check its parser.
2. `1. Manual Patch` for `amazonmusic` and `linkedin`; phone-test both.
3. `src/etc/cleanup.py preview`, review, `apply --token`.
4. #102 (provider watch with and without `-u`), council `same_site` exact host, free council
 seats from `knowledge/handbook/FREE-LLM-APIS-2026-10-v2.md`, release-notes consolidation.
5. Desk leads still unread: `explore.yml` `$PKG`, portal SRI. Packet S2: publisher pins,
 version step-down. Then Edge apkpure refusal, F05/F06, PR53, phone tests, ES File icon, agent
 runner pilot, the unused `TDL_BACKUP` secret.

## Earlier checkpoint: 8 October 2026 (packet W2)

W2 (one pull request) makes every app or patch change two steps (`5. Add target`, then merge),
adds the plain status page, ships MicroG RE with the apps that need it, removes repeated notes,
fixes four silent failures (shipped in W3), and carries W1's onboarding gate, tooling watch and decided leads
([LEADS-2026-10-08.md](LEADS-2026-10-08.md)). Record: [SESSION-2026-10-08.md](SESSION-2026-10-08.md).
Open, in order:

1. W2 merged (#158, merge commit `5e648da5`), W3 follows. Run `Status page data` once; check the page and one `5. Add target` dry change.
2. Amazon Music and LinkedIn: provider from the [scout](onboarding/CANDIDATES-2026-10-08.md),
 then one add run each.
3. #102 (provider watch with and without `-u`), council `same_site` exact host, free council
 seats from `knowledge/handbook/FREE-LLM-APIS-2026-10-v2.md`, release-notes consolidation
 ([plan](CLUTTER-2026-10-07.md)).
4. Desk leads still unread: `explore.yml` `$PKG`, `nightly_report.py`, portal SRI and cache.
5. Packet S2: publisher certificate pins, version step-down. Then Edge apkpure refusal,
 F05/F06, PR53, phone tests, ES File icon, agent runner pilot, the unused `TDL_BACKUP` secret.

## Earlier checkpoint: 7 October 2026, evening (handover)

V2 is on main (PR #156); the council works the pinned desk #154 on a schedule. Everything the
6-7 Oct chat found is in the [session record](SESSION-2026-10-07.md). Open, in order:

1. Desk leads: verify each against the code before any packet. Confirmed but not fixed from the
   [audit ledger](AUDIT-COUNCIL-2026-10-06.md): ci.yml resolve `continue-on-error`; poll-only
   resolve matrix; manual-patch `shadow_plan_required` default; provider-watch `-x -u` (#102);
   portal script integrity and 30-second read cache; watch job without a timeout; classify RISK
   map; obtainium package overrides. New desk leads: explore.yml `$PKG`; APKPure entries for
   Photos and Prime Video; redirect same-site check in council.py.
2. Agent runner pilot ([plan](../council/RUNNERS.md)): OpenCode with the GitHub MCP server,
   read-only, owner-triggered, artifact output only.
3. Pages, release-notes and desk consolidation ([plan](CLUTTER-2026-10-07.md)). Blocked history
   moves: REPORT-2026-09-07 (named in AGENTS.md), AUDIT-2026-09-26 (read by a test).
4. Packet S2: publisher certificate pins on every store path, version step-down.
5. Edge apkpure refusal, #102, F05/F06, PR53, phone tests, ES File icon (monogram), the unused
   `TDL_BACKUP` secret (owner decides).

## Earlier checkpoint: 7 October 2026, afternoon (packet V2)

V1 is on main (PR #153): council desk #154, triage scored 18 of 19 calls right, 17 stale failure
issues and #152 closed, 45 old releases deleted with tags kept (receipt PR #155). Packet V2 tunes
the seats from that score, runs the council on a schedule one job at a time, and moves closed
checkpoints to [history](history/README.md). Open: verify desk leads, packet S2 (publisher pins,
version step-down), Edge, #102, F05/F06, PR53, phone tests, the agent runner pilot
([plan](../council/RUNNERS.md)), Pages and release-notes consolidation.

## Earlier checkpoint: 7 October 2026 (packet V1)

Packet V1 fixes why council seats failed (JSON mode, low reasoning, 404 fall-through, one repair
turn, quoted findings), adds the council `triage` lane, and replaces per-run failure issues with
one standing "Failing:" issue per workflow that closes on the next green run. Its controller
closes the 17 stale per-run failure issues with evidence. Open: verify audit leads, packet S2
(publisher pins, version step-down), Edge, #102, F05/F06, PR53, phone tests, the agent runner
pilot ([plan](../council/RUNNERS.md)), Pages and release-notes consolidation (V2).

## Earlier checkpoint: 6 October 2026, night

Packet S1 is on main (PR #150) and Reddit built green through the second store; #146 is closed.
Packet T1 adds three free council providers, the council `audit` lane over repository shards
(guide: `docs/council/SETUP.md`) and owner-supplied icons for JioHotstar, MX Player and ES File.
Open: verify the council audit findings, packet S2 (publisher pins, version step-down), Edge,
#102, F05/F06, PR53, phone tests.

## Earlier checkpoint: 6 October 2026, evening

Packet R is on main (PR #148); YouTube Music and Facebook 580 built green, Reddit did not (APKPure
lagged one version). Packet S1 adds the second-store chain ([record](SOURCE-CHAIN-2026-10-06.md)).
Open: Reddit green build (#146), packet S2 (publisher pins, version step-down), Edge, #102,
F05/F06, PR53, phone tests.

## Earlier checkpoint: 6 October 2026, packet R

Packet R on main `7b6504e2`: YouTube Music added (see [the decision record](YTMUSIC-2026-10-06.md)),
Facebook pinned to the exact ARM64 store variant (6 Oct section of the
[Facebook record](FACEBOOK-580-2026-09-29.md)), DeArrow ships on YouTube, brand tiles per
[ICON-PROVENANCE.md](ICON-PROVENANCE.md), 5S fixes. Post-merge build results are a comment on the
packet R pull request.

Still open: Reddit Patch apk failures since 5 Oct (#146), a green Facebook 580 build (#105) if the
pin is not enough, the Edge apkpure refusal, #102, F05/F06, PR53, phone tests for YouTube Music
and Facebook 580, and the older items below.

## Previous checkpoint: 1 October 2026

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

First post-merge run (36534562050, see the [session record](history/SESSION-2026-09-29.md)): Prime
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

Start with the [26 September handover](history/HANDOVER-2026-09-26.md): current main after
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
