# Closed-issue audit — shard B

**Scope:** `(assistant sandbox)`, input lines 76–150 inclusive. The slice contains 75 unique issue records; all 75 were accounted for and judged against the supplied issue comments and the 31 Oct 2026 repository tree.

## Counts

| Class | Count |
|---|---:|
| DONE | 41 |
| UNFINISHED | 0 |
| DUPLICATE | 3 |
| BOT-NOISE | 30 |
| WRONG-CLOSE | 1 |

**Collection coverage:** complete for the assigned 75 records (75 unique issue numbers; known assigned total 75; no remaining slice partitions). **Processing coverage:** 75/75 judged; failed/skipped/unjudged: 0.

## UNFINISHED / WRONG-CLOSE

### #262 — WRONG-CLOSE

- **Evidence:** Closed completed after green run 40477224535, but knowledge/STATE.md records the real failure: APKMirror transfer failed twice, then APKPure silently supplied 25.20.0 instead of 26.36.1 and Skip ads failed. W16v later explicitly fixed #262 by exact-version fallback/refusal and fresh APKMirror retry (STATE.md; OPEN-WORK-ARCHIVE-2026-10.md). Green rerun did not establish the root cause was fixed.
- **Next step:** Correct the audit trail to mark the green-only closure as premature and link the W16v root-cause fix/proof; no code change remains on current main.

## Recurring patterns / lessons

- **Alert-per-run noise:** the slice contains many per-run `Failing:`/`Workflow failure:` issues that simply close after a later green run. The V1 close notes for #136–#141 and #147 explicitly describe consolidation into one standing failure issue. Three related reports (#143, #145, #149) point to the same Facebook/Reddit incident tracked under #146.
- **Green is not always root-cause resolution:** #262 is the clear false close. A later green build led to completed closure, but the documented APKMirror→APKPure version fallback issue was fixed by W16v afterward. Keep transient recovery and root-cause resolution distinct in audit notes.
- **Watch failures need cause labels:** #248–#250 had concrete and different causes, fixed in W16n: duplicate repository in Community index, Nightly listing without `-x`, and MCP scout using an unnamed model that returned HTTP 503.
- **Provider reports are observations, not proof of publishability:** #144 records a deliberate DeArrow/default-name decision; #234/#235 preserve provider inventories and build coverage; #252 records a valid owner choice but correctly leaves CCleaner disabled after fingerprint failures. Keep selection decisions, smoke evidence, enabled state, and publication state separate.
- **Superseded snapshots should not be mistaken for dropped work:** #184/#189 were folded into a review and combo list; W15e and later Community/Provider comments point to a standing latest report. Preserve the link to the successor or active tracker when closing old snapshots.

## Grouping ideas

1. Group failure notifications by workflow/incident and record run IDs as comments or children of a standing issue; keep a separate root-cause/fix field so “green again” does not imply fixed.
2. Keep Provider watch and Community index changes in one standing report each, with date-stamped deltas and an explicit successor link; retain the raw run/report parts as history.
3. Group patch-list reports by `(target, provider, package)` and link each to a normalized decision record, smoke result, and enabled/published status. Flag intentionally disabled targets (e.g. CCleaner) as deferred, not “shipped.”
4. Group Council findings by shard, distinguishing unverified advisory leads from verified tracked work, and link superseded audits to the active Council desk.

## Files

- `B.csv`: one row per assigned issue; evidence and next step preserved per record.
- `B.md`: counts, coverage, exception analysis, patterns, and grouping suggestions.
