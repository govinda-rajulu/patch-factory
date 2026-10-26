# Historical open-work reconciliation (26 Oct 2026 list)

Written by an assistant mining agent on 26 Oct 2026 (packet W16m, fifth check of the handover); the
rows are in [OPEN-ITEMS-2026-10-26.tsv](OPEN-ITEMS-2026-10-26.tsv). After it: the MISSING rows went
into items 11 and 12 of the 26 Oct OPEN-WORK checkpoint, and B30 (and in round 8 B27, the FAQ images) was changed to DONE in the table, the counts and its bullet (Failing issue #237
is closed on GitHub, checked 26 Oct; the agent saw only repo records; a Failing issue closes only on a green run of its workflow). The
rest is the agent's text; its file:line references are as of commit 251ee6a and have shifted since.
A round-7 agent repeated the reconciliation independently and got the same 68 rows and counts.

## Coverage

- Processed all 46 `##` sections in `docs/review/OPEN-WORK.md`, including the nine-item “Core engineering still open or partial” section, the owner-preservation section, and the final maintenance section.
- Also reconciled `knowledge/STATE.md`, `knowledge/archive/STATE-2026-09-to-2026-10-24.md`, `docs/review/SESSION-2026-10-25.md`, all `docs/review/history/SESSION-*.md` and `HANDOVER-*.md` open/next-like sections, `docs/review/W17-BRIEF.md`, and section 7 of `docs/review/HANDOVER-2026-10-26.md`.
- Near duplicates are grouped in the TSV. Source section headings/line ranges are retained in each row; later checkpoint text and current files were treated as evidence.
- Ledger rows: 68 unique grouped items (excluding the first 26 Oct consolidated list as a source item); no source section was left unprocessed.

## Counts

| Status | Count |
|---|---:|
| CARRIED | 28 |
| DONE | 22 |
| SUPERSEDED | 7 |
| MISSING | 11 |
| UNKNOWN | 0 |
| **Total** | **68** |

## MISSING — proposed wording for the 26 Oct list

These are older open/partial items not represented by the consolidated list (or not represented with enough specificity to preserve the work):

1. (DONE since: #237 is closed on GitHub.) **B30 — Provider fetch issue #237:** “Re-run/resolve provider fetch issue #237 for oxbow and legendsciber; close it only after a green Explore/fetch run.” Later records show provider selection but retain the two failed fetch records, not a closure.
2. **B47 — F05/F06:** “Finish F05/F06: pre-resolve and consume exact dynamic inputs, observe omitted targets, and qualify a durable successful-publication baseline.” The repository still says F05/F06 is partial.
3. **B48 — Watcher coverage:** “Complete watcher coverage/delta/options evidence for providers, extras and defaults, including universal patches.” The old #102 fix does not close the broader core-engineering gap.
4. **B49 — Same-version Obtainium:** “Test same-version patch-only Obtainium notification and installed-setting migration; do not assume APPVERSION-bBUILDID proves client behavior.” The current re-import item is narrower.
5. **B50 — Qualification trust:** “Finish per-target qualification trust with independent original-APK provenance/attestation and reproducibility evidence.” Mixed-red-run qualification remains explicitly limited.
6. **B51 — Governance/onboarding:** “Audit required-CI/bypass and add-target schema/disabled semantics, including GitLab-primary capability and effective/default approvals.” W17 does not cover this broader governance gap.
7. **B52 — Supply chain/recovery:** “Complete independent source/recovery work: original-APK trust, reviewed alternative-source pilot, restore-tested repo/assets and signing backup, plus phone validation.” Phone validation is separately carried, but recovery/source work is not.
8. **B53 — Reconciliation/cleanup:** “Refresh cleanup inventory with APK-byte backup, review targeted agent guidance/skills, and inspect/decide PR53 separately.” Current item 11 only preserves PR53 as unknown.
9. **B54 — Official artwork:** “Review/record provenance and permitted usage for remaining official app artwork; keep monograms where unavailable.” The ES File monogram is carried, but the broader provenance review is missing.
10. **B55 — Upstream provenance:** “Review upstream attribution, Morphe NOTICE handling and per-provider pinned licence/source records periodically.” Akash’s licence risk is carried, but not the broader review.
11. **B57 — Evidence maintenance:** “Keep evidence links current and label each item shipped/partial/blocked/deferred.” This is the final OPEN-WORK maintenance instruction and is not represented in the 26 Oct list.
12. **B60 — Reproducibility/integration:** “Add/decide reproducible-build and PR integration-test coverage, with explicit acceptance limits.” The historical record and static core section still leave this unfinished.

## UNKNOWN — proposed wording for the 26 Oct list

- None. The one initially ambiguous image-pinning item is **DONE**: `git log --oneline -S'pin the bypass images by digest'` finds `a78c0cc` (“pin the bypass images by digest”), and the current preparing action no longer contains the old Docker image.

## 26 Oct list items that look already done/stale

- No actionable 26 Oct item is evidenced as complete by the repo. The list’s open statuses are consistent with the later handover.
- One line under item 11 is not actually an open task: **“By design, not a bug: a Failing issue comments once per failed run.”** It is a settled policy statement, not work; evidence is `docs/review/OPEN-WORK.md:66-68` and `docs/review/SESSION-2026-10-25.md:51-56`. It should be moved to a policy/notes section or marked “DECIDED”, rather than retained among “Still open” bullets.
- The “Done since, so not carried” text at `docs/review/OPEN-WORK.md:71-74` correctly excludes store-service on-demand startup, second-store additions, zizmor advisory, Qualify per-candidate plans, paresh licence read, FiorenMas review, and replaced Facebook phone-test wording; those are not stale open items.

## Interpretation notes

- `CARRIED` means the older item’s meaning is represented by a numbered item in the first OPEN-WORK section, even where the current wording is condensed (especially item 11).
- `DONE` uses later checkpoint text as evidence when available, as permitted by the brief; it does not imply live phone or external-service verification unless the cited record says so.
- `SUPERSEDED` means a later record deliberately replaced the old wording/configuration. It is not counted as current open work.
