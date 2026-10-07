# Review desk

Every reviewed finding, decision, audit and handover for this repository lives in
this folder. Start at the top. Files under **History** record what was true on
their date; they are not current instructions.

Last indexed **7 October 2026** for the 6-7 Oct handover (council desk, cleanup, V1 and V2). Hygiene record:
[5S audit](AUDIT-5S-2026-09-27.md).

## Start here

| Read | Why |
| --- | --- |
| [SESSION-2026-10-07.md](SESSION-2026-10-07.md) | 6-7 Oct session: packets R to V2, council desk #154, cleanup, findings, wrong calls, coverage limits. Read first. |
| [HANDOVER-2026-09-26.md](history/HANDOVER-2026-09-26.md) | 26 September session handover (history; current state is `knowledge/STATE.md`): what shipped, schedules, cleanup, next steps. A 27 September correction is appended. |
| [SESSION-2026-09-29.md](history/SESSION-2026-09-29.md) | Packet L session: findings, what PR107 shipped, the assistant's wrong calls, and what is still open. |
| [OPEN-WORK.md](OPEN-WORK.md) | Open, partial and deferred work. Newest checkpoint first. |
| [AUDIT-5S-2026-09-27.md](AUDIT-5S-2026-09-27.md) | Repository hygiene audit: what was sorted, corrected, and left for an owner decision. |
| [AUDIT-MICRO-2026-09-27.md](AUDIT-MICRO-2026-09-27.md) | Line-level security and logic audit: signing-secret scope, no runtime installs, silent failures; issue #27/#35/#5 decisions. |
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
| [AUDIT-COUNCIL-2026-10-06.md](AUDIT-COUNCIL-2026-10-06.md) | All 84 findings of the first council audit, each checked at `d2060b82`: 33 confirmed, 6 unclear, 45 refuted. | Leads |
| [CLUTTER-2026-10-07.md](CLUTTER-2026-10-07.md) | Plan to consolidate Pages, release notes and this desk, with every test-pinned phrase. | Plan, not done |

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
| [UNREVIEWED.tsv](UNREVIEWED.tsv) | Patch names not yet reviewed. | Working list |
| [providers/](providers/) | Committed provider name baselines read by Provider watch. | Live input |
| [retention/](retention/) | Release retention and cleanup records, including the 26 September cleanup. | Record |
| [history/](history/) | Closed checkpoints moved out of the desk on 7 Oct 2026 (packet V2); its README lists them. | History |

## History

| Record | What it holds |
| --- | --- |
| [AUDIT-2026-09-26.md](AUDIT-2026-09-26.md) | Post-PR81 audit: archive, wiring, Explore, CI coverage and page fixes; PR53 disposition. |
| [AUDIT-2026-09-07.md](history/AUDIT-2026-09-07.md) | First repository audit. |
| [REPORT-2026-09-07.md](REPORT-2026-09-07.md) | Report from the 7 September audit. |
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
