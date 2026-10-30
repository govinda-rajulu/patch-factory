# patch-factory state

Newest checkpoint first. Each section is a dated snapshot; verify live before acting.

Start here: [KT-2026-10-28.md](../docs/review/KT-2026-10-28.md), then [OPEN-WORK.md](../docs/review/OPEN-WORK.md).

## Opening message (copy into every new chat)

patch-factory. Start from the PATCH-FACTORY-BUILDS skill, knowledge/STATE.md and the newest docs/review/HANDOVER-*.md; controller tools and the assistant sandbox notes are in docs/review/controllers/README.md. Use if/then launchers: one side effect per if/then with its own result line, never `a && b || c`. Get `git bundle --all` of main first; full suite before any handover. Start controllers with nohup and `tail --pid`.

## W16y-b (30 Oct 2026, evening IST): start here

- **W16y-a merged** as #279 (`75fd6dae`, tree `801b1a96`). Owner run RESULT OK; Facebook, Prime Video and Amazon Music (26.36.1, De-Vanced v1.6.2) smokes worked; ES fallback stopped at the coverage floor as designed. Read docs/review/HANDOVER-2026-10-30-W16y-b.md.
- **W16y-b**: provider safety scan on nonpublishing smokes (permissions, hosts, red flags, ClamAV, VirusTotal hash lookup); monthly watched-provider digest with the three Hush providers as watch sources; pin check as a manual report-only probe (schedule after live evidence); 180-day patch-age warning on portal and status; weekly Council model lines; Telegram switched to rahul9999xda (non-Hush, owner 30 Oct evening; smoke build is the phone test). Wrong calls 112 to 117. Nothing published or deleted.
- **Next**: Telegram fallback decision (rahul9999xda on 13.1.1), new-provider ready-PR orchestration, first scheduled runs 1 to 2 Nov, retention apply with the owner's token from 3 Nov, W15g signing split alone.

## W16y-a (30 Oct 2026)

- Removed the unused chooser/community-diff utilities and the dead chooser branch; the full and unreviewed selection-sheet modes remain. The removal record is `docs/review/history/REMOVED-2026-10.md`.
- Moved the closed candidate scout into review history, added the owner decisions record, repaired signer guidance, and added the W16y-b queue (provider gate, digest, pin check, Council report and Telegram survey).
- Completed owner actions recorded for this checkpoint: secret scanning and push protection, `TDL_BACKUP` deletion and merged CCleaner branch deletion. Wrong call 110 is fixed on its failure path.

## W16x (29 Oct 2026, early IST): start here

- **W16w merged** as #275 (`2db6cde8`, tree `728638b2`). Owner run RESULT FINDINGS (Amazon Music only). LinkedIn v1.2.0 with Material You published; phone test passed (Michii Patches in the Me panel). Read docs/review/HANDOVER-2026-10-29-W16x.md.
- **W16x**: store near-version picks bounded to the same release line (Amazon Music 2.36.1 to 2.8.1 refused; Prime Video and Hotstar still build); PR #277 folded (7 switchable names); ES File fallback rushiranpise back (Unlock VIP Lifetime alone); onboarding checker fails closed on a malformed extra_bundles; LinkedIn GmsCore support and Remove gaps and dividers recorded as owner drops; schedules doc; Cloud Shell cleanup record. Wrong calls through 108.
- **Idle on purpose**: Instagram fallbacks (HushGram and oxbow only support 453; a 453 fallback release would lock piko 452.1 out). MX fallback MightyMichs (fingerprint mismatch on 1.93.4). Amazon Music (provider version 2.36.1).

## W16w (28 Oct 2026, night IST)

- **W16v merged** as #268 (`750f3448`). Read docs/review/KT-2026-10-28.md, then docs/review/HANDOVER-2026-10-28-W16w.md.
- **Owner, 28 Oct**: Instagram Home empty (brosssh always-on hides dropped in W16w; switchable patches stay; switch audit docs/review/SWITCH-AUDIT-2026-10-28.jsonl); keep releases and tags this week (no cleanup apply); never drop patches to pass a build; non-Hush providers primary.
- **W16w**: Instagram pinned to APKMirror build 385811006 with every chosen piko patch (Custom font back; the six long-standing exclusions stay); hoo-dles on stable for Prime Video; ES File and CCleaner icons; CodeQL test fix. Wrong calls through 97.
- **Owner devices** unchanged: Android 10 main phone with Signer pin off; Android 11 and 12 devices keep the pin.

## W16v (27 Oct 2026, evening IST)

- **W16u merged** as #267 (`97abdc7c`, tree `1fd9861b`): combo RESULT OK, 3 smokes worked, Pages OK. Probe: 7 open issues (#262 closed), one bad run (the W16p T1 Amazon Music failure).
- **W16v** (this packet): #262 root cause. When the first store resolved version V and failed, the second store is asked for V exactly (APKPure `.../download/V`); any other version prints `STORE_DOWNGRADE_REFUSED store=... got=... wanted=V` and nothing is released. APKMirror retry 2 fetches a fresh download page and link. The attempt reason names the refusal. Probe P2: an empty list is complete, not capped (wrong call 94); open issues, runs and jobs paginated.
- **Evidence**: De-Vanced `SkipAdsPatch.kt` declares no Amazon Music version but requires `GetNextEntityInput` (absent in 25.20.0); APKPure lists 26.36.1 and 26.38.1 while its "latest" label says 25.20.0.
- **Proof**: all 17 apps smoked on the branch (store code, L112), T1 on the merge.
- **Obtainium "Downloaded certificate hash: None"**: Obtainium reads signers with GET_SIGNING_CERTIFICATES only; Android 9 and 10 return nothing for that (docs/review/OBTAINIUM-SIGNER-2026-10-27.md). Portal Signer pin checkbox and docs/obtainium-nopin.json for those phones; upstream issue text ready for the owner.
- **Icons**: five official tiles restored (wrong call 95); probe fetches the owner's nine official URLs into icons/ for the next packet.
- **Run 1 and the fix**: Owner run 1 (27 Oct, 23:37 IST): probe OK (icons 8 of 9), PR #268 opened, 16 of 17 smokes worked, Amazon Music included (#262 fix shown on a real build). Instagram piko failed: the same day APKPure swapped its 452.1.0.53.64 file (base 143.2 MB plus mdpi split became 145.4 MB plus xxhdpi; APKMirror lists a new arm64 build 385914182 uploaded 27 Oct 04:16 UTC beside 385811006), and Piko 3.11.0-dev.3 "Custom font" no longer finds its code (ReactNativeFontRegistrationFingerprint). W16v store code does not choose the APKPure file. Owner call 28 Oct: drop Custom font (instagram-piko exclude-patches, DECISIONS.json N-421628). The fix commit fast-forwards packet/w16v; it smokes Instagram only, applies the cleanup and runs T1. Five official 240 px tiles shipped (Amazon Music, Edge, LinkedIn, Google Photos, Reddit).
- **Owner devices**: Android 10 main phone (most apps): import with Signer pin unticked. Android 11 and 12 devices (MX Player Pro, YouTube, Facebook): keep the pin. Steps in OBTAINIUM-SIGNER-2026-10-27.md.
- **Results**: RESULT FINDINGS = merged, T1 listed failures (never OK). Cloud Shell cuts and the upload order: docs/review/controllers/README.md. Wrong calls 1 to 96: ledger pointer in HANDOVER-2026-10-27-W16u.md.
- **Next**: W15g signing split, mapped in docs/review/W15G-MAP.md (keystore password still reaches the third-party patcher as an argument: HIGH).

## W16u (27 Oct 2026, final repair pass)

- Current packet repairs public attribution, signer guidance, icon provenance, probe safety, controller locking, PR/base binding, pagination and downstream side-effect gates.
- Live main is e6cc9203f6b69f58aa2f8af7be611f5f4f96ae45, tree bf9ffb9063047eecb7ca23b51913b220b09b14c0. Rebuild and rerun gates before owner use.
- Historical dated records are preserved; later corrections live in docs/review/CORRECTION-2026-10-27-W16t.md.

## W16s (27 Oct 2026, afternoon IST): start here

- **Purpose**: expand the owner combo into a bounded handover collector: sanitized open issues and comments, open PRs, recent failed/cancelled runs with bad jobs, fixed run evidence, workflow histories, status branch, local logs, and a fresh main bundle.
- **Fresh main read before work**: `af41c3e794396946ea371a2d2da048378f2ba113`, tree `8025371c6d49fc3a31389d16b0ebe780482d1670`; open cases currently include #263, #262, #233, #218, #213, #182, #154 and #27; no open PRs.
- **W16s changes**: P2 writes sanitized `case-review.json`; combo refuses semantic child success unless both children print `RESULT OK`; tests cover issue/PR separation and redaction. All resources used: fresh live API, official API/CLI docs, repository source, four fresh review agents, focused tests, full suite, and controller rehearsal.
- **Next**: W16s controller runs the T1 after merge; inspect the case-review JSON first, then fix Amazon Music store-version fallback and review the open cases.

## W16r (27 Oct 2026, afternoon IST): start here

- **Read first**: docs/review/HANDOVER-2026-10-27.md (section 0, the W16r addendum, then the rest)
  and docs/review/OPEN-WORK.md (current checkpoint).
- **W16q merged** as #264 (`af41c3e7`, 27 Oct 13:31 IST, tree `8025371c` = packet plus the bot
  file); Validate on main green (run 40470661473). Its combo ran: probe P2 OK (zip of evidence),
  Amazon Music keep-going smoke on the branch worked (run 40470259640, APKMirror, 26.36.1).
  Cleanup preview (2 older releases and tags: facebook 584 older build, tc-combo 26.41.5) not applied.
- **#262 cause, from the log** (the annotation alone misled): APKMirror transfer failed twice (wget exit 8, server error, 0 bytes); the store chain then took APKPure, whose "latest" was 25.20.0 (APKMirror and our release: 26.36.1); patch "Skip ads" failed on it (class `GetNextEntityInput` missing) and the patcher exited 1. The job's error line named the
  first red line, not the one that ended the attempt.
- **W16r** (this packet): `build_attempts.py` names the line that ended the attempt (Morphe's
  abort line, else the last red line) and the store the APK came from; probe P2 CLUE lines and
  the status.json address (the `status` branch) fixed; records corrected; T1 on the merge.
- **MCP scout first attempt**: 503 "high demand", then `TerminalQuotaError` (free tier: 20 requests
  a day on the flash model); the lite model ran; checker: 10 accepted, 29 already wired, 0 dropped.
  Whether the two MCP tools were called is not in the log (non-debug retry).
- **Council**: probe dispatch 40444463398: all 9 seats OK (slowest nemotron 98 s). The 27 Oct
  03:17 UTC scheduled audit never started (none by 07:51 UTC); next 15:17 UTC.
- **Wrong calls**: 90 (89: W16q records called Amazon Music "not a patch, before any patching"
  from the annotation alone. 90: probe CLUE lines let DOWNLOAD_DIAGNOSTIC fill the cap and missed
  Morphe's abort line; its status.json address was Pages, not the `status` branch).
- **Open red**: #262 until a green Batch Patch on main (W16r runs T1 on its merge).
- **Next**: any-version store fallback must not take an older app than the first store resolved
  (pin that version on the second store or refuse the downgrade; all 17 smokes, L112); APKMirror
  retry with a fresh link; MCP quota; YOLO fully off; W15g; W17a and W17b; W18.

## W16q (27 Oct 2026, midday IST)

- **Read first**: docs/review/HANDOVER-2026-10-27.md (this chat's map) and the probe zip the W16q
  combo made (`pf-p2-*.zip`: first live MCP scout and Council probe logs, W16p controller and T1
  logs, scheduled-run history, status.json, bundle of main).
- **W16p merged** as #261 (`697eb875`, 27 Oct 08:29 IST, tree `be1428b2`); the controller ran to
  the end: MCP scout (40444460398) and Council probe (40444463398) dispatched and green as jobs.
- **W16q** (this packet): handover, one-file combo (`docs/review/controllers/build_combo.py`:
  probe then controller, one RESULT line), probe P2 kept in `controllers/owner-probes/`.
- **Watches**: Nightly and Community green since W16n (scheduled Nightly #83 green, started 06:47
  UTC, 5 h late: L024). Council's 03:17 UTC audit had not started by 07:18 UTC.
- **Wrong calls**: 88 (87: told the owner no failure issue was open; #262 was. 88: probe P2 would
  have zipped the T1 test APKs; caught in review round 3, before the run).
- **Open red**: #262 Failing: 9. Batch Patch (W16p T1, Amazon Music at Patch apk: the annotation says
  APKMirror transfer failed, 4 s, no patching); W16q smokes it again.
- **Next**: read the probe zip (MCP first attempt failed after 96 s; did the tools run?); YOLO
  fully off (CLI without the action); W15g; W17a and W17b; W18.

## W16p (27 Oct 2026, morning IST)

- **W16o merged** as #259 (`c24d34f`, 27 Oct 03:28 IST): 17 of 17 smokes, T1 17 of 17 and every
  watch it runs green, cleanup kept the newest release of all 17 apps. Record:
  docs/review/SESSION-2026-10-27.md.
- **W16p** (this packet): Council hard time budget with visible progress; the status page tells a
  review verdict and a GitHub-side failure from a broken automation; MCP scout limited to two read
  tools by policy rules that outrank YOLO (YOLO cannot be switched off under this action); carried store and controller fixes. Evidence: probe P1 (27 Oct).
- **After the merge**: read the dispatched MCP scout run (first live proof of the lockdown) and
  the dispatched Council probe; the next scheduled Council audit (08:47 or 20:47 IST) must finish
  under 50 min and print one line per part and seat.
- **Wrong calls**: 86 (86: disableYoloMode would have stopped the scout; caught before the run).
- **Next**: W15g signing split (own packet, phone test); W17a and W17b Add app; W18. Owner:
  Needs you #233 (five provider choices).

## 26 Oct 2026, evening IST (packet W16o)

- **Main** `5aa5433e` (W16n #257, merged 26 Oct; T1: 17 of 17 apps built, Nightly and Community
  green, #248 and #249 closed by Notify) plus bot commits, plus W16o once merged. MCP scout
  run 40315496589 was dispatched by the W16n controller; #250 closes on its green run.
- **W16o** build hardening: the patcher runs with an allowlisted environment; private temp files;
  store transfers move from wget to curl with the same user agent, referer and cookies, https
  only, at most 10 redirects, a 1024M bound checked after the transfer, retries and a stall
  guard, and a named `STORE_FINAL_HOST` line (no host allowlist: the real CDN hosts are not known
  offline); Docker helpers on 127.0.0.1 and a failed helper stops the build; tool downloads
  https-only, bounded, redirect hosts checked, atomic; FlareSolverr v3.5.2 digest; pup replaced
  by `src/build/html_select.py`; patcher tag and sha256 recorded with optional pins; bundle
  sha256 recorded with optional `expected_sha256`; release tidy apply bound to its preview;
  publishing only from main; onboard review without pull-requests: write; community summaries
  count a doubled repository once.
- **Credits**: owner and architect Govindarajulu K; engineering Anthropic Claude models (CREDITS.md "Who
  built it", README, RESULT.json `built_by`; no banner line, owner 26 Oct).
- **Proof before merge**: the W16o controller smokes all 17 apps on the packet branch (both
  stores and the helpers) before it merges, then T1.
- **Wrong calls**: 85. 85: I first read run 40398219589 as "curl gets 403 from APKMirror on every
  download"; 6 of the 14 APKMirror apps passed on curl (no prepared source), so the cause (client
  fingerprint or load on 14 parallel downloads) is unproven. 84: the third W16o run (26 Oct
  night) smoked 17 apps; APKMirror's download endpoint answered curl with 403 on 8 of 14 apps.
  Nothing merged. APKMirror is back on the base wget request (17 of 17 the day before) plus
  local checks (private candidate, never empty, size bound); APKPure stays on curl (its 3 apps
  passed). L112.
  83: round 1 made a failed store helper fatal (`|| exit 1` on each), which
  ended the build before the FlareSolverr to CloudflareBypass fallback could run; base never
  failed there. Round 4 found it before any run: now only both helpers down refuses store
  access, with a test. 82: the W16o curl move sent the store cookie as a raw header, which curl
  drops on a redirect to another host (wget sent it on every request); round 3 review found it
  before any run, now `--cookie` like wget (curl manual), with a test. 81: the fix for 80 added a test that assumed the stored snapshot had no
  doubled repository; it already had one (epabafree/sabp-eppy-patches, Community report #258), so
  Validate failed again (run 40338726723). Tests are now deltas against the stored snapshot, and
  the full suite was run on a copy that mimics live main. 80: W16n changed how a repository listed twice is counted but kept a test
  that compared the live snapshot to the raw record count; once Community watch stored an index
  with the doubled repository (5960 raw, 5957 merged), Validate failed on the W16o pull request
  (run 40333090933) and would fail on main. Fixed in W16o (L111). Agent errors caught in W16o review: an unsupported wget
  option that would have failed every store download; a separate preflight request without the
  store headers; a guessed CDN allowlist; a 300M bound below real bundle sizes (L110).
- **Next**: W15g signing split; W17a and W17b Add app (map: `docs/review/W17A-MAP.md`); W18.

## 26 Oct 2026, afternoon IST (packet W16n)

- **Main** `f922446e31e9e6a50890ead58b64dd733b17da5e` (W16m #256) plus W16n once merged.
- **W16n** fixes the three red watches by cause: Nightly listed names without `-x` (#249, L104);
  Community refused an index that lists one repository twice (#248, now merged and named, L109);
  MCP scout ran on an unnamed default model that answered HTTP 503 ten times (#250, model named
  with one fallback, L108). Also: watch-state writes through the contents API instead of two
  force-pushing writers; checkout tokens no longer kept; fail-closed token pushes; per-job
  permissions; Rule merge checks the diff against the body; CodeQL #5 and #6; tidy items from
  OPEN-WORK 11. Record: `docs/review/SESSION-2026-10-26.md`; audit with re-rated severities:
  `docs/review/AUDIT-2026-10-26.md`; plan and decisions D1 to D11:
  `docs/review/PLAN-2026-10-26.md`.
- **Review method** for every packet and handover, all repositories:
  `knowledge/handbook/REVIEW-METHOD.md` (laser-scoped agents, WH findings, re-rate agent HIGHs,
  exit on no HIGH or MED). W16n round log: `docs/review/REVIEW-METHOD.md`.
- **After merge**: the W16n controller dispatches 7. Nightly watch, 8. Community watch and MCP
  scout once on main (WATCH_DISPATCH) and does not wait; read each run. A green run closes its
  failing issue (#249, #248, #250) through Notify.
- **Wrong calls**: 79. 79: the MCP scout failure was put down to reading the 2.7 MB index; the log
  showed HTTP 503 before any tool call. 78: a read-only container broke the P0 Alastor listing.
  77: owner answers called lost when he had never answered by comment.
- **Next**: W16o build hardening (patcher env allowlist, pup to a stdlib helper, FlareSolverr
  v3.5.2 digest, release tidy bound to its preview); W15g signing split; W17a and W17b Add app;
  W18 combo planner. Whole list: OPEN-WORK 26 Oct afternoon checkpoint.

## 26 Oct 2026, morning IST (packet W16m, chat handover)

- **Main** `03ee7de16fe3de2c20cd0c568bb023b71113265f` (W16l #255) plus W16m once merged. The 23 to
  26 Oct chat is closed; its map is `docs/review/HANDOVER-2026-10-26.md`.
- **Apps**: 17 enabled and published (W16k batch 40212870923; Instagram on piko and Reddit on
  Morphe again by 40220026589). CCleaner added but disabled until MightyMichs fixes its issue #18.
- **Runs**: 9 runs from the W16l merge to 26 Oct 05:50 UTC, none failed. Only 3 scheduled runs
  started from 25 Oct 18:10 to 26 Oct 06:40 UTC although about 10 crons were due (OPEN-WORK 6c).
  Failure issues #248, #249, #250 close on their next green run; Needs you #233 waits for the owner.
- **W16m**: records only: handover, `docs/review/W17-BRIEF.md` (W17 Add app, W18 combo planner),
  the 25 Oct Actions and agents audits, closed records moved to `docs/review/history/`, STATE before
  25 Oct archived in `knowledge/archive/`, assistant sandbox notes in
  `docs/review/controllers/README.md`, older open items carried (OPEN-WORK items 11 and 12),
  lessons L100 to L103, lesson hashes pinned for L078 to L103.
- **Wrong calls**: 76. 76: the handover called those stale docs "all fixed"; round 7 found eleven
  more. 75: W16j and W16k left current docs stale (Telegram and Truecaller onboarding
  records, council PERSONAS and SETUP, APPS.md picker text, ROADMAP Needs you commands). 73: a docs test run directly ran zero tests and was reported as passing
  (L102). 74: the W17 brief said bot pull requests get no checks; `5. Add target` dispatches
  Validate and Onboarding review itself. 69: "W17" already named the combo planner (now W18). 70: the first handover
  said the assistant sandbox was clean while /tmp still held files. 71: 8 overnight runs claimed, 9
  real. 72: the STATE archive move broke five relative links. Full list: HANDOVER section 5; how the
  handover was checked: `docs/review/REVIEW-METHOD.md`.
- **Next**: W17 owner-only Add app (owner answers the brief's open questions first); W18 combo
  planner; W15g signing split; CCleaner after a provider fix; phone tests. Whole list: OPEN-WORK
  26 Oct checkpoint.

## 25 Oct 2026, late night IST (packet W16l)

- **Main** `19a9b969` (W16k #251 `cb11a66e`, CCleaner #254) plus W16l once merged.
- **W16l**: Status page data no longer red (Notify skips events it never reports); Validate's
  selection-watch test repo has no auto gc (a detached gc raced the temp cleanup). CCleaner: the
  owner keeps Unlock Premium (paid_ok_targets, DECISIONS take, record licence GPL-3.0; Disable
  Telemetry failed on 26.08.0 and the owner removed it), card line "Premium unlocked". CCleaner is disabled until MightyMichs fixes
  its issue #18: both patches miss their fingerprints on 26.08.0 (bundle v1.12.0). "5. Add
  target" now writes the patch names as the card line. Instagram piko holds Hide feed posts and
  Reddit Alastor holds "Reddit native post-menu originals (2026.41.0)": each failed on the app
  version we build, so both apps had shipped from their fallback (W16k smoke and publish batch
  40212870923). W16k publish batch: 17 of 17 apps built and published. Record
  docs/review/SESSION-2026-10-25.md (W16l part). Wrong calls: 68.
- **Next**: W17 one-form Add app (owner-only by GitHub write access; find providers, smoke,
  merge only when green, paid names wait in Needs you); W15g signing split; owner phone tests.

## 25 Oct 2026, night IST (packet W16k)

- **Main** `9ad6af15` (W16j #247) plus bot commits, plus W16k once merged.
- **W16k**: APK picker judges chip, Android and screen together (src/build/variant_pick.py) and
  never keeps a build that does not fit; an APK that needs a newer Android tries the SAME version
  from the other store before any lower one (Key Mapper: APKPure's one 12L file, APKMirror's
  arm64 Android 10+ build). Workflow diet: followers wake only for runs on main, Notify runs
  inside Status page data, Rule merge on its two crons only, Check new patch 2 crons, Council 2
  crons (solo shifts on request); 25 Oct replayed: 299 runs to about 173, a quiet day about 37 to
  21. Agents: an owner-written PR reads the owner's head policy, rule 4 is one build, one line per
  finding, seat plumbing folded, an unchanged review is not re-posted. Failures: Qualify
  NO_RECEIPT is a warning; MCP scout trusts its fresh checkout; Community and Nightly name why.
  Pages: built cards fold real history (what changed, notes, 4 older APKs), Obtainium and MicroG
  cards with one download, date and time everywhere; release notes open with "Built ...".
  Facebook Unlock app icons kept (owner); Photos AMOLED kept from Akash. Controller: at most 2
  smokes per app, publish dispatched after the merge, not waited for. Record
  docs/review/SESSION-2026-10-25.md (W16k part). Wrong calls: 65.
- **Next**: W15g signing split; owner phone tests; W17 combo planner.

## 25 Oct 2026, evening IST (packet W16j)

- **Main** `829ec099` (W16i #244) plus W16j once merged.
- **W16j**: owner decision memory (src/patches/DECISIONS.json), Needs you v2 (groups, tables,
  `yes all`, group and except commands, quiet comments), Telegram HushTelegram, Key Mapper
  legendsciber, Truecaller heval99 primary, Reddit Alastor, Instagram oxbow, Photos Akash (no
  licence declared), Amazon Music paid names (owner approved), Qualify plan per candidate,
  keep_going smokes, three-line report heads. Record docs/review/SESSION-2026-10-25.md. Wrong
  calls: 60 (L089 to L092 are lessons, not wrong calls).
- **Next**: owner answers Needs you with the new commands; phone tests (Truecaller with MicroG RE
  first, Telegram HushTelegram, Reddit 41, Instagram piko, Facebook 584); W15g signing split; W17
  combo planner.

## Older snapshots

29 Sep to 24 Oct 2026: [archive/STATE-2026-09-to-2026-10-24.md](archive/STATE-2026-09-to-2026-10-24.md) (verbatim, historical).
