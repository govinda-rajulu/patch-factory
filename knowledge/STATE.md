# patch-factory state

Newest checkpoint first. Each section is a dated snapshot; verify live before acting.

## Opening message (copy into every new chat)

patch-factory. Start from the PATCH-FACTORY-BUILDS skill and knowledge/STATE.md. Use if/then launchers: one side effect per if/then with its own result line, never `a && b || c`. Get `git bundle --all` of main first; full suite before any handover.

## 9 Oct 2026, evening (packet W7; start here)

- **Base** W6 (#163, head `3e14e809`) plus packet W7 (one pull request). The owner runs one
 controller, `pf-w7.py`: merge #163, push and merge W7 after its checks, dispatch Manual Patch
 for `amazonmusic` and `linkedin`, collect their log lines and a repository inventory. Record:
 the W7 section of `docs/review/SESSION-2026-10-09.md`.
- **Versions** (owner design): newest the provider supports, or the store's newest when the
 provider lists none. Above the phone cap the build steps down, at most 3 lower versions
 (`src/build/version_steps.sh`, notice `VERSION_STEP_DOWN`). Fixed: `min_sdk_ceiling`,
 `max_app_version` when set, exact `version_code` pins (no step-down). Amazon Music and LinkedIn
 have no pins now.
- **Pages**: the MicroG RE card shows one download for the chosen icon, CPU and channel; all six
 files and checksums are folded. `docs/status.html` (W4 redirect) deleted.
- **Also in W7**: council redirect key stays on the exact host; Explore refuses malformed inputs;
 `docs/SCHEDULES.md` (generated, checked); two old review records moved to `history/`.
- **Next**: read the controller's RESULT file; OPEN-WORK 9 Oct (W7) list.

## 9 Oct 2026, afternoon (packet W6)

- **Base** main `1e08ef02` (W5 #162 merged). Packet W6 is one pull request on top. Record:
 `docs/review/SESSION-2026-10-09.md`; open items: `docs/review/OPEN-WORK.md` (9 Oct, W6).
- **Builds since W5**: LinkedIn built (run 37912428867, 4.1.1255.1); phone test pending.
 Amazon Music failed the native check (run 37912474736): `lib/arm64-v8a/libInit.so` is the six
 bytes `4.6.14`, unchanged by patching. W6 accepts only that shape under that file name.
- **Cleanup**: second apply on 9 Oct deleted 22 releases and 22 tags (receipt
 `~/work/run-logs/cleanup-receipt-20261009T091933Z.json` on the owner box).
- **Status**: build workflows are keyed by app. A run whose only failures are app jobs marks
 those apps, not the automation; a failure outside an app job still marks the workflow.
- **Next**: OPEN-WORK 9 Oct (W6) list, in order. Rebuild Amazon Music first.

## 9 Oct 2026 (packet W5, session close)

- **Base** main `be8aaa44` (W4 #160 merged). Packet W5 is one pull request on top. Record: the W5
 section of `docs/review/SESSION-2026-10-08.md`; open items: `docs/review/OPEN-WORK.md` (9 Oct).
- **Start every packet** by asking the owner for `git bundle --all` of main; run the full suite
 and a headless Pages render in the sandbox before handing anything over.
- **Apps**: 17 targets. LinkedIn pinned to 4.1.1255.1 (4.1.1258 needs Android 12L); Amazon Music
 pinned to 26.34.0 (its patches say "Any" version). Neither has built yet: Manual Patch both,
 phone-test, Amazon only on a throwaway account (owner keeps its two paid-tier patches).
- **Cleanup rule** (owner): each app keeps its two newest builds; everything older is purged.
 `src/etc/cleanup.py preview` then `apply --token`. Done once on 9 Oct (4 releases, 96 tags).
- **Branches**: only `main` and `status`. Merged branches are archived on the owner box
 (`~/work/pf-archive`, INDEX) before deletion.
- **Disable/enable** now pass the suite; a disabled app keeps folders, record, logo and fallback
 entry.
- **Next**: OPEN-WORK 9 Oct list, in order.

## 8 Oct 2026, afternoon (packet W4)

- **Base** main `18670c23` (W2 #158 and W3 #159 merged). Record: the W4 section of
 `docs/review/SESSION-2026-10-08.md`.
- **Sandbox sees the whole repo now.** The owner uploads `git bundle --all` of main; the
 assistant runs every test and renders Pages in a headless browser before handing a packet over.
- **Pages**: Builds and Watch read `status.json` (grouped, newest first, capped lists, the data's
 age). A failure stays listed until a later run of the same app or automation works; when its
 workflow changed since, the row asks for one confirming run. `status.html` redirects there.
- **MicroG RE card**: stable and pre-release, six files each (icon or no icon; ARM64, ARMv7,
 universal) with sha256. Obtainium import: three steps, icon choice. Before W4 the ARM64 and
 ARMv7 downloads were broken by MicroG's 7.2 file names.
- **New apps**: Amazon Music (RookieEnough/De-Vanced) and LinkedIn (heyymichii/michii-patches).
 Not built yet: run `1. Manual Patch` with `amazonmusic` and `linkedin` after merge.
- **Adding apps really is two steps now**: `app.py add` writes the store-fallback entry and the
 APKMirror org/name; tests count targets from `src/targets.json` (`tests/target_counts.py`).
- **Cleanup**: `src/etc/cleanup.py preview`, then `apply --token`. Reddit page diagnostic and two
 unused patch folders removed.
- **Next, in order**: (1) merge W4, run Status page data, open the page. (2) Manual Patch for
 amazonmusic and linkedin; if Amazon Music will not install, add `Rename shared permissions`.
 (3) cleanup preview and apply. (4) #102, council `same_site`, free council seats, release-notes
 consolidation. (5) S2 publisher pins; Edge, F05/F06, PR53, phone tests.

## 8 Oct 2026 (packet W2)

- **Base** main `4bdb82b8`. Record: `docs/review/SESSION-2026-10-08.md` (applied and dropped
 hunks at its end). Leads decided: `docs/review/LEADS-2026-10-08.md`.
- **App changes are two steps**: run `5. Add target` (add, patch, disable, enable, remove),
 merge its pull request. Tool: `src/etc/app.py`; how-to `docs/APPS.md`. `1. Manual Patch`
 takes a typed id.
- **Status in plain words**: `docs/status.html`, data from `Status page data` on the `status`
 branch.
- **Onboarding gate**: every new app, provider or patch name needs its record and the agent
 review (`Onboarding review`).
- **Tooling watch** (09:59 IST): pinned tools follow new releases, pre-releases included, as PRs.
- **Requirements**: `needs_microg` and `installed_package` in `src/targets.json` are the one home.
- **Next, in order**: (1) W2 merged (#158), W3 follows; run `Status page data` once and open
 the page. (2) Amazon Music and LinkedIn: pick a provider from the scout, one add run each.
 (3) #102 baselines with and without `-u`, council `same_site` exact host, free council seats
 from the v2 guide. (4) S2 publisher pins, version step-down. (5) Edge, F05/F06, PR53, phone
 tests, ES File icon, agent runner pilot.

## 7 Oct 2026, evening (handover)

- **Main** `fec38e60` (PR #156, V2) plus the handover packet. 15 targets. 7 council seats on 6
  providers; probe after V2: 6 of 7 ready (open seat flaky). Desk #154 pinned: the schedule posts
  one audit shard at 08:47 and 20:47 IST and triage on Monday 08:47 IST. Open issues: #27
  (standing nightly report), #102, #142, #154.
- **Session record**: `docs/review/SESSION-2026-10-07.md` (what shipped, findings, wrong calls 1-8,
  coverage limits). Audit ledger: `docs/review/AUDIT-COUNCIL-2026-10-06.md`. Clutter plan:
  `docs/review/CLUTTER-2026-10-07.md`. Provider facts: `docs/council/PROVIDERS.md`. Runner plan:
  `docs/council/RUNNERS.md`. Generic lessons: `knowledge/handbook/FREE-LLM-AGENTS.md`.
- **Next, in order**: (1) read the desk after a few rotations; packet the leads that reproduce,
  first the open confirmed items in OPEN-WORK. (2) Agent runner pilot (RUNNERS.md). (3) Pages and
  release-notes consolidation (CLUTTER plan). (4) S2: publisher certificate pins, version
  step-down. (5) Edge, #102, F05/F06, PR53, phone tests, ES File icon.
- **openskip** (its own repo and chat): keys stored; its packet (more seats, drop duplicate
  `sweep.yml`, GitHub Models remnants) is recorded in openskip `knowledge/STATE.md`.

## 7 Oct 2026, afternoon (V1 results, packet V2)

- **V1** merged as PR #153 (main `1fe3d4a7`). Probe: 6 of 8 seats ready. Council desk #154.
  Triage vs the owner-checked list: council calls 18 right of 19, 2 split; seats nemotron 95%,
  codestral 92%, command 81%, gemini 8/8, open 6/6, gpt 2/5. 17 stale failure issues and #152
  closed. 45 old releases deleted by owner choice, tags kept (receipt PR #155, main `bb7a477a`).
- **What V1 runs showed**: dispatching 11 audit shards at once ran the free tiers out (gemini
  busy on every part, NVIDIA busy or cut). kimi's four NVIDIA models are never served to this key.
  One seat repeated one generic issue on five lines of a file.
- **Packet V2**: kimi seat removed (7 seats), gpt leaves triage (40%), the open seat gets room to
  answer, busy retries wait for the provider's own hint (max 60 s), repeated rows collapse into one,
  and council runs on a schedule: one audit shard twice a day and triage on Monday mornings, all on
  desk #154 (`desk_job`). Closed checkpoints moved to `docs/review/history/`.
- **Next**: (1) read the desk as shards rotate; packet what reproduces. (2) Agent runner pilot.
  (3) S2. (4) Edge, #102, F05/F06, PR53, phone tests.

## 7 Oct 2026 (packet V1)

- **Base** main `d2060b82` (PR #151, packet T1). Audit issue #152: 8 of 11 shards posted; only
  `codestral` and `command` answered every part. Causes: unreadable or cut JSON (gpt, gemini,
  nemotron, open), NVIDIA 404 for kimi-k2.6 that stopped the seat, Groq over budget. (All 11
  shards did post; "three posted nothing" came from truncated page reads. Corrected in V2.)
- **Packet V1**: council JSON mode with per-seat reasoning effort and refusal fallback, 404 falls
  through, one repair turn, findings must quote the cited file (`verify_quotes`), seat `jobs`, a
  `triage` mode (`docs/council/TRIAGE.md`), audit deadline 30 minutes. `notify-failure.yml`: one
  standing "Failing:" issue per workflow. usque zip checked against its release digest; `#` lines
  in selection files are skipped. Agent runner research: `docs/council/RUNNERS.md`.
- **Next**: (1) read the triage score and the re-run audit shards; packet what reproduces.
  (2) V2: agent runner pilot, Pages and release-notes consolidation. (3) S2. (4) Edge, #102,
  F05/F06, PR53, phone tests.

## 6 Oct 2026, night (packet T1)

- **Base** main `97e7fd06` (PR #150, packet S1). Reddit run 37452203181 green through the second
  store (APKPure failed, APKMirror 2026.40.0 arm64 480-640dpi, 19 patches); #146 closed.
- **Keys** (7 Oct, owner scripts keys-k1/k2): all six free provider keys tested and stored in both
  repositories. The 7 Oct probe had 4 of 6 seats: NVIDIA-hosted `mistral` 404, `minimax` unserved.
- **Packet T1**: council seats for Mistral, Cohere and Groq; `mistral` dropped, `minimax` becomes
  `kimi` (eight seats, six providers, budgets per seat), a new `audit` mode over 11 repository shards (`src/council/shards.json`, prompt
  `docs/council/AUDIT.md`), and the key and lane guide `docs/council/SETUP.md`. Owner-supplied
  store icons for JioHotstar, MX Player and ES File, recorded in `docs/review/ICON-PROVENANCE.md`;
  a tile ships only if its fetch passed the PNG gate on the controller's run.
- **Council audit results** are comments on one issue opened by the T1 controller. They are
  leads: each is verified against the code before any fix packet.
- **Next**: (1) review the audit comments and packet the findings that reproduce. (2) Packet S2:
  publisher certificate pins, version step-down. (3) Edge. (4) #102. (5) F05/F06, PR53. (6) Phone tests.

## 6 Oct 2026, evening (packet R results, packet S1)

- **Packet R** merged as PR #148 (main `eb3d3fb5`). Post-merge builds: YouTube Music run
  37448728870 green (`yt-music-v9.40.51-b2026100600000000037448728870000001`, no excluded name in
  the notes); Facebook run 37448742969 green on the pinned ARM64 variant, #105 closed; Reddit run
  37448758026 failed: APKPure had no 2026.40.0 link and the qualified fallback admits only
  2026.38.0. #125, #143, #145, #100 and #144 closed. Nothing phone-tested.
- **Packet S1**: a failed store now tries the other mapped store with the same gates before the
  qualified fallback; APKMirror mappings for Reddit, Instagram, Edge. Record:
  `docs/review/SOURCE-CHAIN-2026-10-06.md`. Its controller rebuilds Reddit and closes #146 on green.
- **Next**: (1) packet S2: publisher certificate pins on every store path, version step-down.
  (2) Edge apkpure refusal (now also has APKMirror). (3) #102. (4) F05/F06, PR53. (5) Phone tests.

## 6 Oct 2026 (packet R)

- **Base** main `7b6504e2` (community bot commit on 5 Oct). Packet R adds target 15, `ytmusic`
  (YouTube Music, Morphe), pins Facebook's exact store variant (arm64-v8a, 240-640dpi, code
  475019344; the old input was the armeabi-v7a row 475019268), lets YouTube ship DeArrow (owner),
  adds local brand tiles for 12 apps with sources in `docs/assets/NOTICE.txt`, and a 5S pass.
  Records: `docs/review/YTMUSIC-2026-10-06.md`, the 6 Oct section of
  `docs/review/FACEBOOK-580-2026-09-29.md`, `docs/review/ICON-PROVENANCE.md`.
- **Build results** for ytmusic, facebook and reddit after the merge are posted as a comment on the
  packet R pull request by its controller. Read that comment first; this file was written before.
- **Reddit** (Patch apk failures since 5 Oct, #143/#145/#146): not diagnosed in this packet. adobo
  `v1.6.0-dev.4` (4 Oct) supports 2026.40.0. The controller saves the failed-step log; diagnose next.
- **Issue hygiene by the controller**: #125 into #105; #143 and #145 into #146; #100 superseded by
  #142. #105 and #146 close only on a green build of their targets. #27, #102, #142, #144 stay.
- **Next**: (1) read the PR comment; Reddit diagnosis from the saved log. (2) Edge apkpure refusal.
  (3) #102 universal-patch blind spot. (4) F05/F06, PR53. YouTube Music and Facebook 580 are not
  phone-tested.
- **Lessons** 10 to 14 in [LESSONS.md](LESSONS.md).

## 3 Oct 2026 (packets P and Q on 1 Oct, then two days of scheduled runs)

- **main** `09bf31ba`: the monthly keepalive bot commit (`.keepalive` only) on `b4104369`, which is
  PR124 packet Q (setup-java 6.0.1 in five workflows and in the `preparing` composite) on PR123
  packet P and PR122. Dependabot #103 closed as superseded: it bumped the workflows but not the
  composite, so Validate's action-ref contract failed.
- **Closed 1 Oct**: #96 and #97 (council tests), #83 (superseded by #102), #82 (#100 is newer),
  #114 (YouTube recovered on the 30 Sep release). Packet P folded the Facebook run records into #105.
- **Facebook still fails after packet P**: scheduled runs on 2 and 3 Oct failed at Patch apk only
  (#129 to #132; every other app built). Dropping `De-Vanced Settings` was not enough. The phone
  stays on 490. Next is a fresh diagnosis from the newest job log, starting with variant
  475019268 vs 475019344 and which chosen patch pulls in the AMOLED theme patch.
- **Open**: #27 (nightly standing issue, keep open), #100, #102, #105, the Facebook run records.
- **Next**: (1) Facebook, above; close the run records into #105 once diagnosed. (2) Edge apkpure
  bundle refusal. (3) Owner confirms YouTube's two newly applied patches (Playback buffer, Restore
  original titles), then #100 and #102. (4) Dependabot `directory: "/"` does not scan
  `.github/actions/*`; `directories` would, but a reported upstream bug splits grouped PRs across
  directories. Owner decides. (5) F05/F06, PR53.
- **Lessons** 7 to 9 added to [LESSONS.md](LESSONS.md).
- **Chats**: from 1 Oct the owner keeps one assistant chat per repo. A patch-factory chat starts
  here and never carries openskip rules.

## 1 Oct 2026, packet P

- **main**: PR122 (roadmap docs) on `2b58d78b`, then packet P: `De-Vanced Settings` dropped
  from Facebook's include list. Cause and limits: `docs/review/FACEBOOK-580-2026-09-29.md`.
- **Same controller (`pf-packet-p-v1`), each step behind its own gate**: merge Dependabot #103
  (setup-java 6.0.1, refs only); close the Facebook run records whose only failure is Patch apk
  (#109, #115 to #121 when written) as covered by #105; close #98, #101, #104 on the published
  Prime Video 3.0.470.357; close #106; close #99 on a green Nightly after 29 Sep. The run's
  ledger line in `~/work/run-ledger.txt` says which steps ran.
- **Left open**: #105 until a green Facebook build; #114 (its 29 Sep YouTube failure is
  undiagnosed); #102; Edge apkpure refusal; F05/F06; YouTube's two new patch names.

## 1 Oct 2026, 01:30 IST (planning only, no code)

- **main** `2b58d78b` (PR113 packet O), unchanged.
- **Scheduled runs on 30 Sep**: Facebook failed at Patch apk twice (#118, #119). YouTube
  21.39.522 was republished by run 36716967959 with two newly applied patch names (Playback
  buffer, Restore original titles); owner to confirm they were expected.
- **New**: [ROADMAP.md](ROADMAP.md) and [handbook/AGENT-TOOLING.md](handbook/AGENT-TOOLING.md)
  (1 Oct tool review). No workflow, selection or code change.

## 29 Sep 2026, 13:50 IST

- **main** `6af68340` (tree `90d7786a`): PR112 (the 13:45 checkpoint below and lessons 4 to 6
  in `LESSONS.md`) on PR110 `f2a31fee` (this folder) on PR111 packet N `5301b5c8`, which
  sits on PR108 packet M and PR107 packet L.
- **Facebook variant lead, unproven**: the 580 input was version code 475019268, but
  `docs/review/FACEBOOK-580-2026-09-29.md` records 475019344 as the ARM64 build the new
  patches target. Same version name, different build. The `FdsContextColor580Fingerprint`
  failure may come from the variant, not the patch selection. Check the variant before
  changing patches.
- **Next**: (1) Facebook: confirm the downloaded variant and which selected patch depends
  on the AMOLED theme patch. (2) Edge: why the shadow apkpure bundle fetch refuses in 23 s
  while real Edge builds publish. (3) With owner OK, close #98, #101, #104 on the Prime
  build; #105 after Facebook builds; #99 after the next Nightly. Then #102, #103, F05/F06,
  PR53.
- **Notes**: packet O's controller prints its real base in MAIN_MOVED (the 13:45 cosmetic
  item). Scheduled runs started about five hours late on 29 Sep; a manual dispatch (owner
  OK) gets evidence quickly. The 29 Sep packet ledger is `~/work/pf-archive/LEDGER.txt`;
  later scripts use `~/work/run-ledger.txt` per WORKING-AGREEMENT.md.

## 29 Sep 2026, 13:45 IST (end of the packet N session)

- **main**: PR111 packet N merged as `5301b5c8` (tree `fd6d4d01`): session record, OPEN-WORK,
  review desk house rules 5 to 7, lesson L036. Then PR110 merged (this `knowledge/` folder).
- **Run 36534562050 shadow reasons**, read from the saved job log (owner copy:
  Cloud Shell `~/work/pf-archive/run-36534562050-reasons.txt`):
  - **Edge**: `source inputs failure: existing store fetcher refused (exit 1 after 23s,
    source apkpure, type bundle)`. The shadow resolver was offered a bundle and refused it.
    Open question: should the shadow path accept bundles? Real Edge builds are a separate path.
  - **Facebook input**: 580.0.0.51.74, code 475019268, 90,549,610 bytes. Right version name,
    unproven build: `docs/review/FACEBOOK-580-2026-09-29.md` names code 475019344 (ARM64) as
    the target of the new patches, so this may be a different variant (see 13:50 above).
    The patch-time failure (`FdsContextColor580Fingerprint` in the AMOLED theme patch, pulled
    in by one of the four chosen patches) is still open. Nothing was published; the phone
    stays on 490.
  - **Prime Video input**: 3.0.470.357, code 470000357. Built; not phone-tested.
  - **AdGuard**: 4.14.68, pinned to rushiranpise as intended.
  - Also observed: esfile 4.4.3.7, hotstar 26.06.08.2, instagram 439.0.0.37.89, keymapper
    4.2.1, mxplayer 1.93.4, photos 7.92.0.977185651, reddit 2026.38.0, telegram 12.10.1,
    truecaller-combo 26.10.6, youtube 21.39.522.
- **Next**: find which chosen Facebook patch depends on AMOLED; decide on bundle handling for
  Edge; close #98, #101 and #104 with the Prime build as evidence (owner OK needed). Then the
  rest of `docs/review/OPEN-WORK.md`.
- **Council**: the PR110 review got 4 of 6 seats (mistral 404, gpt unavailable). Check seats.
- **Cosmetic**: packet N's MAIN_MOVED message still names `93fc2b98`; fix in the next packet.
- **Cloud Shell cleanup done**: packet L v2 and M clones removed, their controllers deleted,
  ledger line in `~/work/pf-archive/LEDGER.txt`; the stopped L v1 folder and the ~1000 MB
  artifact zips are kept (owner decides later).

## 29 Sep 2026, 12:30 IST

- **main** `1b8e42c3` (tree `1ae504b4`): PR108 packet M merged 06:53Z (council lessons
  L028 to L035 and `docs/review/history/SESSION-2026-09-29.md`). Its parent `90e12e57` is PR107
  packet L (poll pin, Prime Video `release=NNN`, Facebook 580, nightly name check, council
  j4, shadow reasons). Full detail: `docs/review/history/SESSION-2026-09-29.md`.
- **Next**: first post-merge evidence (Prime Video build, Facebook 580 build, Edge's printed
  reason, AdGuard not rebuilding on prereleases). Then close #98, #101, #104, #105 with that
  evidence and #99 after the next Nightly. Then #102 (provider watch blind to universal
  patches), Dependabot #103, F05/F06 full fingerprints, PR53.
- **Council**: six free seats, advisory comments only; GitHub Models is retired (its endpoint
  answers a bare "OK"; never seat it). Free model catalogues churn; check the provider's
  deprecation page before debugging transport.
- No issue writes, dispatch, cleanup, settings, signing or selection change without fresh
  owner approval.

### Owner-side material that is deliberately not in git

- Signing backups: owner-held copies (restore untested). Never commit or request them.
- Cloud Shell `~/work/pf-archive/` (moved 29 Sep, index `INDEX-20260929T065453Z.txt`):
  executed controllers, their RESULT files and work folders, `pf-backup-*.tar.gz`, the
  original MX APK, and `pf-evidence-review-gaj8a7s5` (about 1000 MB of downloaded Actions
  artifact zips; some may be the only copies of builds whose releases were deleted).
  Binaries never go into git; deleting them is an owner decision.

## Before 29 Sep 2026

See `docs/review/history/HANDOVER-2026-09-26.md`, `docs/review/OPEN-WORK.md` and
[archive/skills/PATCH-FACTORY-BUILDS.md](archive/skills/PATCH-FACTORY-BUILDS.md).
