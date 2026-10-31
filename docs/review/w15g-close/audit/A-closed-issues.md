# Closed-issue audit — shard A (input lines 1–75)

## Coverage and verdict totals

- Assigned collection: first 75 JSONL lines, in source order. Read and classified: **75/75** records; unique issue numbers; no unreadable/unjudged rows. The supplied file may contain additional rows outside this shard; they were not part of this assignment.
- Processing: **75 accounted / 75 classified**; **0 failed or skipped**. No independent authoritative total for the full file was asserted.
- Classification is issue-local: later unrelated OPEN-WORK is not treated as unfinished unless it is the same reported work. Mitigated failures are noted as such.

| Class | Count |
|---|---:|
| DONE | 21 |
| UNFINISHED | 0 |
| DUPLICATE (of #N) | 32 |
| BOT-NOISE | 22 |
| WRONG-CLOSE | 0 |

**Summary:** 21 DONE; 32 DUPLICATE; 22 BOT-NOISE; 0 UNFINISHED; 0 WRONG-CLOSE.

## UNFINISHED and WRONG-CLOSE findings

None found in the 75-record shard. There are no next steps to assign under those classes. The `next_step` column is `—` for all other verdicts.

## Recurring, lesson-worthy patterns

1. **Repeated run failures became issue noise.** The Facebook 580 failure recurred across a long run of scheduled issues (#105, #106, #109, #114–#121, #125–#132, #134–#135). Comments trace the family to a De-Vanced/AMOLED fingerprint mismatch and then an ARM-variant mismatch; PR148 pinned ARM64 build 475019344 and a later build went green. Repo `src/targets.json` still carries that exact pin. Later comments state failures now flow to one standing “Failing: <workflow>” issue closed by the next green run.
2. **Provider discovery false positives were cross-host identity mismatches.** Reports for paresh/GitLab appeared unwired because the community index named the same author’s GitHub repo (#2, #17, #26); host-agnostic matching was added. Most other discovery rows in this shard say providers were already in `src/targets.json`; one report was an Android-TV-only bundle (#20).
3. **Provider/community watcher reports accumulate and supersede earlier snapshots.** #40 → #82 → #100 → #142 and #50/#71 → #83 → #102 illustrate report churn; close older observations against the latest complete run. #102’s specific omitted-universal-patches bug was fixed and baselines reseeded, but current `docs/review/OPEN-WORK.md` still lists broader provider/extra/default coverage and actionable delta work as open—this is a separate remaining project item, not evidence the #102 bug itself stayed unfixed.
4. **Upstream patch incompatibility may be mitigated without being fixed upstream.** #35/#36 share the Remove Debug Info `IllegalAccessException`; current `src/patches/QUARANTINE` retains it for ES File and MX Player. Keep the record as “mitigated/quarantined,” not “upstream fixed.”
5. **Actionable grouping ideas:** dedupe failure issues by workflow + target + normalized cause, retaining each run ID under one standing failure tracker; group provider observations by watcher run and mark older snapshots superseded; group discovery reports by `(package, provider identity, host-normalized)` so duplicates/host aliases are suppressed.

## Traceability notes

- Every row and evidence string is in `A.csv`, preserving source order and the input metadata columns requested.
- Current-state checks used `docs/review/OPEN-WORK.md`, `docs/review/history/OPEN-WORK-ARCHIVE-2026-10.md`, `src/patches/DECISIONS.json`, `knowledge/STATE.md`, `src/targets.json`, and `src/patches/QUARANTINE` where relevant. Historical audit evidence includes `docs/review/AUDIT-5S-2026-09-27.md` and `docs/review/AUDIT-MICRO-2026-09-27.md`.
- The audit does not claim that all builds were phone-tested: for example, the Facebook 580 closure explicitly says “not phone-tested”; the separate phone-test work remains in current OPEN-WORK.
