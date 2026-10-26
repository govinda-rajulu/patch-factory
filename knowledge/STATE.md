# patch-factory state

Newest checkpoint first. Each section is a dated snapshot; verify live before acting.

## Opening message (copy into every new chat)

patch-factory. Start from the PATCH-FACTORY-BUILDS skill, knowledge/STATE.md and the newest docs/review/HANDOVER-*.md; controller tools and the assistant sandbox notes are in docs/review/controllers/README.md. Use if/then launchers: one side effect per if/then with its own result line, never `a && b || c`. Get `git bundle --all` of main first; full suite before any handover. Start controllers with nohup and `tail --pid`.

## 26 Oct 2026, evening IST (packet W16o; start here)

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
- **Credits**: owner and architect Govindarajulu K; engineering ClickUp Brain on Anthropic's Claude (CREDITS.md "Who
  built it", README, RESULT.json `built_by`; no banner line, owner 26 Oct).
- **Proof before merge**: the W16o controller smokes all 17 apps on the packet branch (both
  stores and the helpers) before it merges, then T1.
- **Wrong calls**: 82. 82: the W16o curl move sent the store cookie as a raw header, which curl
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
