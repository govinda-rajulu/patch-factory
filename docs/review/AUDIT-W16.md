# W16 audit: every workflow, what it costs, who reads it (23 Oct 2026)

Data: the owner's read-only probe pf-audit (23 Oct 16:42Z, main 822c5f3c): every run since 23 Sep
(1673 runs, 22 workflows including GitHub's own), jobs of the newest builds, open issues with
comments by author. Minutes run from the start of the last attempt to its end. Six pull request
runs that show 99 or 1455 minutes are left out: their end time moved when the pull request closed.

## The short version

- 30 days, about 3060 runner minutes. Builds are the point; most of the rest is reporting.
- Nobody reads the watch issues. The owner has commented on none of the five standing watch
  issues (#27 Nightly 48 bot comments, #182 Selection 18, #213 Provider, #218 Tooling, #221
  Community) and once on the Council desk #154 (7 Oct).
- 2. Check new patch failed 49 of 118 runs (41 percent). A run is red when any one app fails.
- A one-app Check new patch run (39914680513) ran 17 shadow jobs (28.6 job-minutes, every app's
  APK downloaded) before its single build.
- Status page data ran 458 times (about 15 a day), 441 of them after another workflow, 127 cancelled.

## Every workflow

| Workflow | Trigger | Runs in 30 days | Minutes | Writes | Read by | W16 |
| --- | --- | --- | --- | --- | --- | --- |
| 2. Check new patch | 4 crons a day, manual | 118 (49 failed) | 801 | releases, Pages records | owner (phone, Obtainium) | keep; shadow jobs only for apps that build |
| Council | 6 crons a day, pull requests, manual | 126 | 748 | comments on #154, pull request reviews | owner reads rarely (1 comment) | keep; one desk job at a time; output caps removed |
| 3. Validate | pull requests, pushes to main, manual | 173 | 467 | checks | controllers, owner | keep (bot commits land on main directly) |
| Status page data | after 16 workflows, daily, manual | 458 (127 cancelled) | 376 | status branch | Pages (docs/portal.js), community watch | after build and watch workflows only; daily run still reads all |
| 1. Manual Patch | manual, called by Batch and Check | 66 | 246 | releases | owner | keep |
| 9. Batch Patch | manual | 10 | 110 | releases | owner | keep |
| Notify on failure | after 11 workflows | 283 | 58 | failure issues | owner | keep (never suppress, L061) |
| pages-build-deployment | GitHub, on docs change | 82 | 51 | Pages | visitors | keep |
| 7. Nightly watch | daily | 38 | 37 | issue #27 | nobody | keep as collector; its issue keeps state; findings go to Needs you |
| Onboarding review | pull requests | 22 | 33 | review comments | controllers | keep |
| 10. Selection watch | daily | 21 | 32 | adopt pull requests, issue #182 | Rule merge (pull requests); nobody (issue) | collector only; findings go to Needs you |
| Qualify published shadow baselines | after 3 build workflows | 178 (91 skipped) | 24 | qualified records on releases | shadow comparison | keep (skips are free) |
| 11. Rule merge | 4 crons a day, after 3 workflows, manual | 24 | 17 | merges rule pull requests | n/a | 2 crons a day (safety net for L069) |
| 6. Provider watch | Mondays | 15 | 16 | issue #213 | nobody | collector only; findings go to Needs you |
| CodeQL, Dependabot | GitHub | 9 + 9 | 30 | alerts, pull requests | owner | keep |
| Tooling watch | daily | 23 | 8 | issue #218, update pull requests | nobody (issue) | keep collector (issue holds dedupe state); findings go to Needs you |
| 8. Community watch | Mondays | 13 | 7 | issue #221, index snapshot | nobody | ranks providers per app (official first); findings go to Needs you |
| 4. Explore, 5. Add target | manual | 3 + 1 | 1 | issues, pull requests | owner | keep |
| Keepalive | monthly | 1 | 0.2 | a commit | nobody: bots commit to main every day | manual only |
| Needs you (new) | daily 10:29 IST, manual | - | - | one issue | owner | new: the only place to look |

## Where the build minutes go

- Check new patch, one app (39914680513, 10.5 min wall): Plan 0.5, 17 shadow jobs 28.6
  job-minutes (APK preparation 9.3), one build 3.7. After W16 the shadow job runs only for the app
  that builds: about 26 job-minutes and 3.5 wall minutes less on that run, nothing on a run with
  no builds instead of 28.6.
- Batch of 17 (39913450300, 10.8 min wall): Patch apk 36 job-minutes, Preparing 14. No shadow jobs.
- The patcher JAR is cached by targets.json hash, not by version; source APKs are not cached.
  Caching both by exact version and sha needs the resolved packet to expose cache keys first: open.

## Wrong facts found

- targets.json Reddit note "adobo covers reddit alone": false. Official Morphe v1.48.0 lists 31
  Reddit patches for 2026.42.0 down to 2026.10.0 (docs/review/PATCHES-reddit-morphe.txt, owner's
  live run 23 Oct). W16: Morphe primary, Adobo fallback.
- Tooling watch label for morphe-patches said "YouTube, YouTube Music": now includes Reddit.
- docs/review/onboarding/facebook.md named 583 and HushFacebook 0.14.0: now 584.0.0.51.56, 0.17.0.

## Not covered

- Why each of the 49 red Check new patch runs failed: needs job logs; T1 after W16 reports per app.
- Pages wording beyond the release card and footer (W16 words change covers the card and notes).

## Why Check new patch went red (49 of 118, 23 Sep to 23 Oct)

The audit lists 49 failed runs. An agent read the audit files and the public job records (W16c, 24 Oct); it checked the recorded jobs first and used the public Actions job records where the audit did not include the failed step. A run is counted once below, by the main stop that made that run red.

| cause | runs | first-last date | failing job/step | fixed by (packet) or OPEN |
|---|---:|---|---|---|
| Prime Video output identity check rejected the release marker | 4 | 2026-09-28 to 2026-09-28 | build (primevideo) / Patch primevideo / Verify finished APK identity | fixed before W15 (28 Sep records) |
| Facebook patch could not match the AMOLED-theme fingerprint (De-Vanced Settings pulled it in) | 30 | 2026-09-29 to 2026-10-06 | build (facebook) / Patch facebook / Patch apk | fixed before W15 (29 Sep to 6 Oct records) |
| Amazon Music resolver returned an empty/duplicate version field | 4 | 2026-10-10 to 2026-10-10 | Resolve shadow dependencies (amazonmusic) / Resolve exact dependency files (no APK or signing) | W15i |
| LinkedIn shadow input did not match the version the build had to step down to | 2 | 2026-10-11 to 2026-10-11 | Resolve shadow dependencies (linkedin) / Resolve exact patcher-input APK (shadow only) | OPEN (combo planner and ceiling memory) |
| Several source-download checks failed together: Photos transfer was incomplete and Telegram/Facebook certificates could not be read | 1 | 2026-10-14 to 2026-10-14 | Resolve shadow dependencies (photos); build (telegram) / Patch telegram; build (facebook) / Patch facebook / Resolve exact patcher-input APK (shadow only); Verify source APK before signing secrets; Patch apk | W15b (transfer retry); W15c (read certificate from original source) |
| Facebook fallback built, but publishing refused the older fallback because the merged source could not prove the pinned certificate | 2 | 2026-10-20 to 2026-10-20 | build (facebook) / Patch facebook / Releasing APK files | W15c |
| Reddit release was refused because 2026.41.0 was older than the published 2026.42.0 | 1 | 2026-10-22 to 2026-10-22 | build (reddit) / Patch reddit / Releasing APK files | W15f; W16b caps Reddit at 2026.41.0 |
| The polling step got a temporary empty provider-date answer | 2 | 2026-10-22 to 2026-10-22 | Plan / Poll every opted-in target | W15h |
| Reddit could not use the newer 2026.42.0 input on this phone ceiling; its older release was also refused by the shelf guard | 1 | 2026-10-22 to 2026-10-22 | Resolve shadow dependencies (reddit); build (reddit) / Patch reddit / Resolve exact patcher-input APK (shadow only); Releasing APK files | W16b |
| Morphe created an extra data folder beside its patcher; the resolver treated those unlisted files as an invalid packet | 2 | 2026-10-23 to 2026-10-23 | Resolve shadow dependencies (every app) / Resolve exact dependency files (no APK or signing) | W15i |

### Takeaways
- Most failures came from one old Facebook 580 patch dependency; the workflow correctly stopped instead of publishing a bad APK.
- A second cluster was input selection: Prime Video’s marker, Amazon Music’s empty version, LinkedIn’s step-down, and Reddit’s Android ceiling.
- Some red runs were real download/signing problems, not patcher bugs: Photos transfer and unreadable certificates.
- GitHub sometimes returned empty transient provider data; later retries made that visible instead of treating it as a real change.
- By W15i/W16b, the resolver and Reddit/Facebook safeguards were explicit; LinkedIn ceiling memory and the signing split remain open.
