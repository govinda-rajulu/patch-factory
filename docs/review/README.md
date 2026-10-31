# Review desk

Every reviewed finding, decision, audit and handover for this repository lives in
this folder. Start at the top. Files under **History** record what was true on
their date; they are not current instructions.

Last indexed **31 October 2026** for packet W15g ([HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md)) and earlier that day for packet W16y-c ([HANDOVER-2026-10-31-W16y-c.md](HANDOVER-2026-10-31-W16y-c.md)); **30 October 2026** for packets W16y-a and W16y-b ([HANDOVER-2026-10-30-W16y-b.md](HANDOVER-2026-10-30-W16y-b.md); [DECISIONS-2026-10-30.md](DECISIONS-2026-10-30.md); [OPEN-WORK.md](OPEN-WORK.md)); **29 October 2026** for packet W16x ([HANDOVER-2026-10-29-W16x.md](HANDOVER-2026-10-29-W16x.md)); **28 October 2026** for packet W16w ([HANDOVER-2026-10-28-W16w.md](HANDOVER-2026-10-28-W16w.md)); **27 October 2026** for packet W16v (addendum in [HANDOVER-2026-10-27-W16u.md](history/HANDOVER-2026-10-27-W16u.md)); earlier that day for packets W16p and W16q ([HANDOVER-2026-10-27.md](history/HANDOVER-2026-10-27.md)) ([SESSION-2026-10-27.md](history/SESSION-2026-10-27.md)); before that **26 October 2026** for packets W16n and W16o ([SESSION-2026-10-26.md](history/SESSION-2026-10-26.md)); earlier that day for packet W16m (chat handover; closed W15 and W16 records moved to `history/`); before that **25 October 2026** for packet W16h; before that **20 October 2026** for W15b; earlier, **10 October 2026** for packets W9 to W12 and handover H12 (controller toolkit in `controllers/`) and packet W13 (retention receipts indexed in `retention/README.md`; agent docs moved to `history/`). Hygiene record:
[5S audit](AUDIT-5S-2026-09-27.md).

## Start here

[HANDOVER-2026-10-31-W16z.md](HANDOVER-2026-10-31-W16z.md) is the current packet pointer (W16z). [HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md) holds W15g (signing split). [HANDOVER-2026-10-31-W16y-c.md](HANDOVER-2026-10-31-W16y-c.md) holds W16y-c. [HANDOVER-2026-10-30-W16y-b.md](HANDOVER-2026-10-30-W16y-b.md) holds W16y-a and W16y-b. [HANDOVER-2026-10-29-W16x.md](HANDOVER-2026-10-29-W16x.md) is the preceding W16x pointer; [HANDOVER-2026-10-28-W16w.md](HANDOVER-2026-10-28-W16w.md) the W16w one. [HANDOVER-2026-10-27-W16u.md](history/HANDOVER-2026-10-27-W16u.md) holds W16u and W16v. Do not run older combos.


| Read | Why |
| --- | --- |
| [OBTAINIUM-SIGNER-2026-10-27.md](OBTAINIUM-SIGNER-2026-10-27.md) | 27 Oct: why Obtainium shows "Downloaded certificate hash: None" (Android 9 and 10), what W16v ships, upstream issue text. |
| [W15G-MAP.md](W15G-MAP.md) | 27 Oct: signing split (W15g) implementation map, file by file against main `97abdc7c`; the next packet. |
| [SIGNING-SPLIT.md](SIGNING-SPLIT.md) | W15g signing isolation design and packet acceptance steps. |
| [KT-2026-10-28.md](KT-2026-10-28.md) | Knowledge transfer of the 26 to 28 Oct chat: owner rules, devices, packet flow, history, open owner calls, wrong calls 91 to 119 and the W16w decision sheet. Read first. |
| [SWITCH-AUDIT-2026-10-28.jsonl](SWITCH-AUDIT-2026-10-28.jsonl) | Every chosen patch (660): in-app switch or always on, default, hides content; sources upstream READMEs and code. |
| [HANDOVER-2026-10-28-W16w.md](HANDOVER-2026-10-28-W16w.md) | Preceding W16w pointer: W16v outcome, T1 findings and causes, what W16w changes, wrong call 97. |
| [HANDOVER-2026-10-31-W16z.md](HANDOVER-2026-10-31-W16z.md) | W16z: pin probe fix, failure-issue reasons, portal cleanups, issue forms and labels, housekeeping, records. |
| [HANDOVER-2026-10-31-W15g.md](HANDOVER-2026-10-31-W15g.md) | W16y-c result and W15g pointer: signing split (Patch without key, Sign with apksigner, Publish without key), gates and owner phone test, W16z list; Result section: merged as #283, 17 of 17 smokes, first split Telegram publish. Read first. |
| [w16z/README.md](w16z/README.md) | 31 Oct: W16z records: pin probe and Reddit findings, #154 safeLink triage, UI pass, scored agent trials, removed files. |
| [w15g-close/README.md](w15g-close/README.md) | 31 Oct: W15g close-out folder: planning reports (W16z inputs, W17 console design), the 282-record issue and PR audit, review rounds R1 to R8, round-4 scenario reports, smoke probe. |
| [HANDOVER-2026-10-31-W16y-c.md](HANDOVER-2026-10-31-W16y-c.md) | W16y-b result and W16y-c pointer: Telegram phone test and publish, scan host fix, pin check through the store reader, push retry, wrong calls 118 and 119. |
| [HANDOVER-2026-10-30-W16y-b.md](HANDOVER-2026-10-30-W16y-b.md) | W16y-a result and W16y-b pointer: provider scan, digest, pin check, patch age, Council lines, Telegram survey, wrong calls 112 to 117, what is not built. |
| [TELEGRAM-SURVEY-2026-10-30.md](TELEGRAM-SURVEY-2026-10-30.md) | Read-only Telegram provider survey. Owner, 30 Oct evening: rahul9999xda v1.17.0 primary (non-Hush); see onboarding/telegram.md. |
| [HANDOVER-2026-10-29-W16x.md](HANDOVER-2026-10-29-W16x.md) | W16x pointer: W16w result, Amazon Music fail-closed cause, near-version guard, owner follow-ups and current limits. |
| [DECISION-REVIEW-2026-10-29.md](DECISION-REVIEW-2026-10-29.md) | W16x read-only review of the standing owner decisions: downsides, safer alternatives and ten owner questions. Changes nothing. |
| [DECISIONS-2026-10-30.md](DECISIONS-2026-10-30.md) | Owner decisions for W16y: pin checks, fallbacks, retention, Council, Telegram, provider admission and completed owner actions; split into W16y-a and W16y-b. |
| [HANDOVER-2026-10-27-W16u.md](history/HANDOVER-2026-10-27-W16u.md) | W16u and W16v records: live main then, repairs, owner runs 1 to 3. |
| [CORRECTION-2026-10-27-W16t.md](CORRECTION-2026-10-27-W16t.md) | 27 Oct dated correction: current public credits, withdrawn unlicensed icons, W15 vs W15h re-import wording, CI is not a phone test. Dated records stay as written. |
| [HANDOVER-2026-10-27.md](history/HANDOVER-2026-10-27.md) | 26 to 27 Oct chat handover (W16n to W16r): how to start the next chat, where things stand, what shipped, owner asks, wrong calls 77 to 90, lessons L108 to L114, afternoon addendum (W16r), open work. Read first. |
| [HANDOVER-2026-10-26.md](history/HANDOVER-2026-10-26.md) | 23 to 26 Oct chat handover (W16 to W16l): how to start the next chat, where things stand, what shipped, owner decisions, wrong calls 51 to 76, lessons, open work, what is not covered. |
| [REVIEW-METHOD.md](REVIEW-METHOD.md) | How a handover is checked: the old self-review, the independent-agent method that replaced it, the exit rule, and the W16m and W16n round logs. Read before any handover check. |
| [OPEN-ITEMS-2026-10-26.md](OPEN-ITEMS-2026-10-26.md) | 26 Oct reconciliation of every open item in all OPEN-WORK sections and the STATE, session and handover records (68 grouped: carried, done, superseded, missing), with its table [OPEN-ITEMS-2026-10-26.tsv](OPEN-ITEMS-2026-10-26.tsv). |
| [W17-BRIEF.md](W17-BRIEF.md) | Plan for the owner-only Add app flow from Pages (W17), with its open questions, and the W18 combo planner. Next packet. |
| [AUDIT-ACTIONS-2026-10-25.md](AUDIT-ACTIONS-2026-10-25.md) | Workflow runs of 25 Oct counted mid-day (298) by workflow and conclusion: the basis of the W16k run diet. |
| [AUDIT-AGENTS-2026-10-25.md](AUDIT-AGENTS-2026-10-25.md) | 42 agent and bot points from 23 to 25 Oct classified real, false, infra, stale, duplicate: the basis of the W16k agent changes. |
| [SESSION-2026-10-27.md](history/SESSION-2026-10-27.md) | 27 Oct morning: W16o result and packet W16p (Council shared deadline, status-page verdict and external rows, MCP scout held to two read-only tools by policy rules that outrank YOLO, carried transfer and controller items, four review rounds, wrong calls 84 to 86, L113, L114); midday and afternoon: W16p result and packet W16q (handover, one-file combo, probe P2, review round 3, wrong calls 87 and 88); afternoon: W16q result, probe zip read, packet W16r (wrong calls 89 and 90). |
| [SESSION-2026-10-26.md](history/SESSION-2026-10-26.md) | 26 Oct afternoon: packet W16n (three red watches fixed by cause, watch-state through the contents API, workflow token hardening, Rule merge diff check, CodeQL fixes, review rounds, wrong calls 77 to 79, L108, L109). |
| [W17A-MAP.md](W17A-MAP.md) | 26 Oct: W17a Add app mapped to the code (existing files and functions, gaps, tests, risks, packet split), by a read-only agent; verify before use. |
| [PLAN-2026-10-26.md](PLAN-2026-10-26.md) | 26 Oct: all-phases plan in WH form and the owner's decisions D1 to D11 (packet chain W16n, W16o, W15g, W17a/b, W18). |
| [AUDIT-2026-10-26.md](AUDIT-2026-10-26.md) | 26 Oct: nine-agent audit, every finding re-rated against the code, and where each went (W16n, W16o, W15g). |
| [SESSION-2026-10-25.md](history/SESSION-2026-10-25.md) | 25 Oct: W16h, W16i and W16j (owner decision memory, Needs you groups, HushTelegram, legendsciber, heval99 primary, keep-going smokes). |
| [AUDIT-W16.md](AUDIT-W16.md) | W16 audit: every workflow, runs and minutes in 30 days, who reads it, what W16 changes. |
| [MCP-PLAN.md](MCP-PLAN.md) | W16d research: MCP servers for groundwork (read-only GitHub scout, fetch), pins read 24 Oct, pilot plan. Built manual-only in W16g; its first green owner run is still to come. |
| [SESSION-2026-10-24.md](history/SESSION-2026-10-24.md) | 23 to 24 Oct: W16 on dev/w16 (audit, Reddit on Morphe, shadow narrowing, plain words, Needs you, council caps, fewer runs). History. |
| [W16-BRIEF.md](history/W16-BRIEF.md) | 23 Oct owner brief after W15i: state, wrong calls 49 and 50, diagnosis, the W16 plan. History. |
| [HANDOVER-2026-10-23.md](history/HANDOVER-2026-10-23.md) | 20 to 23 Oct chat handover (W15b to W15i), 48 wrong calls. History. |
| [SESSION-2026-10-23.md](history/SESSION-2026-10-23.md) | 23 Oct: packet W15i (shadow resolver tool folder L076, Facebook 584, Reddit 42 retired, CodeQL fixes, L077). History. |
| [WIP-W15-2026-10-17.md](history/WIP-W15-2026-10-17.md) | 17 Oct: packet W15 work in progress. History. |
| [SESSION-2026-10-22.md](history/SESSION-2026-10-22.md) | 22 Oct: packet W15e (readable bot reports per [REPORT-STYLE.md](REPORT-STYLE.md), Rule merge fixes, agent personas, one release per app; signing split designed in [SIGNING-SPLIT.md](SIGNING-SPLIT.md)), then W15f (Rule merge counts as bot drift, council v3 from [OUTSIDE-REPOS-2026-10-22.md](OUTSIDE-REPOS-2026-10-22.md)). |
| [SESSION-2026-10-21.md](history/SESSION-2026-10-21.md) | 21 Oct: packets W15c and W15d (W15d: exact bundle version, 11. Rule merge, reserved names, [HISTORY-AUDIT-2026-10-21.md](HISTORY-AUDIT-2026-10-21.md); W15c: W15b result and T1 findings, publisher pin at preparation, adopt pending branch, longest build first, parallel smoke) and [AUDIT-2026-10-21.md](AUDIT-2026-10-21.md) (security, speed, tool freshness, Facebook splits). History. |
| [SESSION-2026-10-20.md](history/SESSION-2026-10-20.md) | 20 Oct: packet W15b (#188 and #141 causes from the job logs, transfer and merge reasons, pinned certificate fails closed, council probe per model, auto-adopt by name and description, owner decisions, W15c plan, wrong calls 31 to 34, L062 to L065). History. |
| [SESSION-2026-10-11.md](history/SESSION-2026-10-11.md) | 11 Oct: W13 results, packet W14 (Reddit universal and store step-down, Nightly false UNKNOWN, ranking, reminders, publisher pins, agent review, one home for repeated text and release tidy, Obtainium card, automation wiring, agent spec and fix lane). History. |
| [SESSION-2026-10-17.md](history/SESSION-2026-10-17.md) | 17 Oct: knowledge bank of the W15 chat (timeline, findings, verified facts, wrong calls 26 to 30, lessons L058 to L061, owner rules). History. |
| [W16-WATCHES.md](W16-WATCHES.md) | W16: one daily Needs you issue, artifact-based collector reports, retained stateful watch issues, and community provider ranking. |
| [SESSION-2026-10-10.md](history/SESSION-2026-10-10.md) | 10 Oct: packet W13 (lost patches dropped by name, provider fallback, Selection watch, pf-t1). |
| [SESSION-2026-10-09.md](history/SESSION-2026-10-09.md) | 9 to 10 Oct: packets W6 to W12 and handover H12 (W12: coverage-first version choice; H12: owner decisions, phone tests, controller toolkit). Before that, 9 Oct: packets W6 to W9 (W9: routine cleanup, retention preview retired, run-log filter, notices). Earlier: packet W6 (Amazon Music `libInit.so` marker, build status keyed by app, second cleanup). |
| [SESSION-2026-10-08.md](history/SESSION-2026-10-08.md) | 8 Oct session: packet W2 (two-step app changes, plain status page, MicroG shipped where needed, silent failures, onboarding gate, tooling watch, leads decided). History. |
| [CANDIDATES-2026-10-08.md](history/CANDIDATES-2026-10-08.md) | Archived community-index candidate scout for Amazon Music and LinkedIn. |
| [SESSION-2026-10-07.md](history/SESSION-2026-10-07.md) | 6-7 Oct session: packets R to V2, council desk #154, cleanup, findings, wrong calls, coverage limits. History. |
| [HANDOVER-2026-09-26.md](history/HANDOVER-2026-09-26.md) | 26 September session handover (history; current state is `knowledge/STATE.md`): what shipped, schedules, cleanup, next steps. A 27 September correction is appended. |
| [SESSION-2026-09-29.md](history/SESSION-2026-09-29.md) | Packet L session: findings, what PR107 shipped, the assistant's wrong calls, and what is still open. |
| [OPEN-WORK.md](OPEN-WORK.md) | Open, partial and deferred work. Newest checkpoint first. |
| [OPEN-WORK-ARCHIVE-2026-10.md](history/OPEN-WORK-ARCHIVE-2026-10.md) | Verbatim archive of the pre-5S open-work checkpoints (October 2026). |
| [AUDIT-5S-2026-09-27.md](AUDIT-5S-2026-09-27.md) | Repository hygiene audit: what was sorted, corrected, and left for an owner decision. |
| [AUDIT-MICRO-2026-09-27.md](AUDIT-MICRO-2026-09-27.md) | Line-level security and logic audit: signing-secret scope, no runtime installs, silent failures; issue #27/#35/#5 decisions. |
| [PROVIDERS-2026-10-09.md](PROVIDERS-2026-10-09.md) | Every app's providers and alternatives from the community index, new and removed names, the watch's missing universal patches (#102), one Truecaller, owner calls open for W11. Read first for patch work. |
| [PROVIDER-DELTAS-2026-09.md](PROVIDER-DELTAS-2026-09.md) | Upstream patch-name changes waiting for owner classification. |

## Decisions and gates

| Record | What it holds | State |
| --- | --- | --- |
| [RESOURCE-DECISION-2026-09-19.md](RESOURCE-DECISION-2026-09-19.md) | ES File and MX Player resource-patch exclusions and the reasoning. | Current decision |
| [DECISIONS-youtube-morphe.tsv](DECISIONS-youtube-morphe.tsv) | Per-patch YouTube review rows. | Reference; the PR47 exclusion wins over older rows |
| [DECISIONS-reddit-morphe.tsv](DECISIONS-reddit-morphe.tsv) | Per-patch Reddit review rows. | Reference |
| [ICON-PROVENANCE.md](ICON-PROVENANCE.md) | Which app icons ship as brand tiles, their sources, and which stay monograms. | Current gate |
| [SOURCE-CHAIN-2026-10-06.md](SOURCE-CHAIN-2026-10-06.md) | Second store with the same gates (S1) and the publisher-pin and version step-down plan (S2). | Current decision |
| [YTMUSIC-2026-10-06.md](YTMUSIC-2026-10-06.md) | YouTube Music target: patch review, exclusions with reasons, and the YouTube DeArrow decision. | Current decision |
| [controllers/](controllers/) | How packets reach the owner: the controller template, a fake GitHub for rehearsal, the local suite and the headless render. | Current tool |
| [onboarding/](onboarding/) | Onboarding records: one per target for every new app, provider or patch name; rules and template in its README. | Current gate |
| [AUDIT-COUNCIL-2026-10-06.md](AUDIT-COUNCIL-2026-10-06.md) | All 84 findings of the first council audit, each checked at `d2060b82`: 33 confirmed, 6 unclear, 45 refuted. | Leads |
| [CLUTTER-2026-10-07.md](CLUTTER-2026-10-07.md) | Plan to consolidate Pages, release notes and this desk, with every test-pinned phrase. | §2 and the notice part of §3 done in W14 (SESSION-2026-10-11 item 10); §1 retention and §4 desk archive still a plan |
| [LEADS-2026-10-08.md](LEADS-2026-10-08.md) | Every open audit and desk lead with a decision: keep, fixed in W2, or later with its evidence. | Current decision |

## APK source admissions

| Record | What it holds | State |
| --- | --- | --- |
| [FACEBOOK-580-2026-09-29.md](FACEBOOK-580-2026-09-29.md) | Facebook moved to 580.0.0.51.74; owner-chosen patches, the dropped settings patch, and the 6 Oct exact ARM64 variant pin. | Current |
| [APK-SOURCE-FALLBACKS-2026-09-26.md](APK-SOURCE-FALLBACKS-2026-09-26.md) | Exact-version source fallbacks shipped in PR86. | Current |
| [APK-SOURCE-ADMISSIONS-2026-09-26.md](APK-SOURCE-ADMISSIONS-2026-09-26.md) | Admission record for the PR86 fallbacks. | Current |
| [APK-SOURCE-ADMISSION-PHOTOS-2026-09-26.md](APK-SOURCE-ADMISSION-PHOTOS-2026-09-26.md) | Photos fallback with its exact signer-rotation pair (PR88). | Current |
| [APK-SOURCE-METADATA-2026-09-26.json](APK-SOURCE-METADATA-2026-09-26.json) | Machine-readable metadata for the admitted sources. | Current |
| [source-qualifications/](source-qualifications/) | Per-source qualification records. | Current |

## Inventories and watcher baselines

| Record | What it holds | State |
| --- | --- | --- |
| [PATCHES.tsv](PATCHES.tsv) | Tabular patch inventory snapshot. | Snapshot |
| [PATCHES-youtube.txt](PATCHES-youtube.txt) | YouTube bundle listing snapshot. | Snapshot |
| [PATCHES-reddit-morphe.txt](PATCHES-reddit-morphe.txt) | Reddit bundle listing snapshot. | Snapshot |
| [UNREVIEWED.tsv](UNREVIEWED.tsv) | Patch names not yet reviewed; legacy input: still read by `src/etc/selection_writer.py` via `review_apply.py`; owner decisions now live in `src/patches/DECISIONS.json`; regenerate only from a live provider listing. | Working list |
| [providers/](providers/) | Committed provider name baselines read by Provider watch. | Live input |
| [retention/](retention/) | Cleanup receipts (releases, tags, Pages deployments, branches), indexed in its README. | Record |
| [w16z/](w16z/) | W16z records (31 Oct); index in its README. | Record |
| [w15g-close/](w15g-close/) | W15g close-out records (31 Oct): planning reports, issue and PR audit, review rounds, round-4 scenarios; index in its README. | Record |
| [history/](history/) | Closed checkpoints moved out of the desk on 7 Oct 2026 (packet V2); its README lists them. | History |
| [REMOVED-2026-10.md](history/REMOVED-2026-10.md) | W16y-a removal record for the unused chooser and community-diff utilities. | History |

## History

| Record | What it holds |
| --- | --- |
| [AUDIT-2026-09-26.md](history/AUDIT-2026-09-26.md) | Post-PR81 audit: archive, wiring, Explore, CI coverage and page fixes; PR53 disposition. |
| [AUDIT-2026-09-07.md](history/AUDIT-2026-09-07.md) | First repository audit. |
| [REPORT-2026-09-07.md](history/REPORT-2026-09-07.md) | Report from the 7 September audit. |
| [SESSION-2026-09-06.md](history/SESSION-2026-09-06.md) | Session record, 6 September. |

## House rules

1. One dated file per audit, decision or handover, named `KIND-YYYY-MM-DD.md`.
   Never rewrite a dated record; append a dated correction instead.
2. List every new file or folder here in the same PR.
   `tests/review_index_contracts.py` fails **3. Validate** when something in this
   folder is unlisted or a link here points nowhere.
3. No private chats, secrets, signing material or raw captures in this folder.
4. Configured, approved, applied, published and phone-tested are different states.
   Say which one a record proves.
5. Chat sessions are disposable. Before one ends, its findings, decisions and open items
   move into this folder, and its lessons into `docs/council/LESSONS.md`, through a reviewed
   PR. The assistant's memory keeps pointers, not copies.
6. Knowledge that also applies to another personal repository is copied there by that
   repository's own reviewed PR, never edited from here. Repository-specific rules stay put.
7. Owner-run scripts clean up after a DONE result: they remove their own upload and working
   clone and keep RESULT.json and logs. After a stop they keep everything.
