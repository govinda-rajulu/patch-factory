# Patch Factory housekeeping survey

Read-only survey; no repository files were changed.

## Scope and confidence

- Checkout: `(assistant sandbox)`; working tree was clean. `HEAD` is `74addf36c4586e8c42a94245380cb146ee40f818` on `packet/w16yc`, and `origin/HEAD` also points to `packet/w16yc`. There is no local `main` or `origin/main` ref. The requested “current main” therefore could not be independently verified; findings below describe this checked-out snapshot.
- External status input: `(assistant sandbox)`; its own `generated_at` is `2026-10-30T20:50:28Z`, not the 31 Oct date in the directory name.
- Documentation collection is exhaustive for root `*.md`, `docs/**/*.md`, and `knowledge/**/*.md`: 148 files (root 6 / 67,628 bytes; docs 113 / 980,004 bytes; knowledge 29 / 264,921 bytes), total 1,312,553 bytes. Last per-file dates below are the result of `git -C repo log -1 --format=%cs -- <path>`.
- Link accounting covers explicit Markdown inline links `[text](path)` in those same 148 files. It checked 432 relative destinations; 380 point to in-scope Markdown files (the inbound counts below sum to 380), 36 Markdown files have zero inline inbound links, and no missing relative targets were found. This does not count prose/code references or reference-style link definitions as inbound links.
- No docs/knowledge/root Markdown page was found that consists only of a “moved to” / “see X” redirect. The short-page and redirect-wording scans found no redirect-only page.

## Prioritized housekeeping list

### P0 — reconcile the retention policy before the first apply

**Fix the policy prose to the implementation, then keep the generated preview as the deletion authority.** Current `src/etc/cleanup.py` constants and logic are:

- Keep the newest **3** releases per app (`KEEP=3`); if all three protected builds are fallback releases, protect the newest readable primary as well.
- Only consider older releases at least **7 days** old (`MIN_RELEASE_AGE_DAYS=7`); malformed/young publication dates are kept.
- Keep the newest **3** GitHub Pages deployment records (`KEEP_DEPLOYMENTS=3`); older records are marked inactive before deletion.
- Delete eligible packet/dev branches only when their head is in `main` and no open PR uses them.
- Delete tags for removed releases and orphan build tags; preserve non-build tags. The retired-builds file also names one Reddit `2026.42.0` release before `2026-10-23T12:00:00Z`, if it is still present and passes the age guard.

This disagrees with both `RECOVERY.md` (“two newest builds”, “newest 5” Pages deployments) and the opening policy text in `src/etc/cleanup.py` (“one per app”, “newest 5”). `src/etc/cleanup.py`’s constants are the live behavior; correct the canonical recovery table and stale docstring/comments, and update any current-facing copy. Do not edit the dated `docs/review/DECISION-REVIEW-2026-10-29.md` as if it were current policy; preserve it as a dated record or add a dated correction.

`retention.yml` is preview-first. Apply is blocked until after 2026-11-02 UTC, and then requires the repository owner to dispatch with `confirm=apply` and the exact token in the one current Retention preview issue. The Python tool rereads the live lists, refuses a stale token, writes a receipt first, and stops on the first failed deletion. Use that owner-confirmed flow only; do not delete releases/tags/deployments/branches by hand.

### P1 — archive closed records in place of deleting them

Move-only candidates (preserve content and repair links/index entries; no deletions):

1. `docs/review/PROVIDER-DELTAS-2026-09.md` — its header says **Closed, 21 October**, says it is a record only, and states new names are handled by Selection watch. It still has a stale old review queue. Move under `docs/review/history/` and update `docs/review/README.md` plus its inbound references.
2. `docs/review/HISTORY-AUDIT-2026-10-21.md` — a closed audit ledger still outside `history/`; archive it and update links from the provider-deltas record and historical session notes.
3. `docs/review/SESSION-2026-10-25.md` — its own “Closed 26 Oct” section says the chat is closed. Move to `history/`, repair links from `knowledge/STATE.md`, the handover, and the review index.
4. The closed checkpoint cohort is still at the review-desk root: `docs/review/SESSION-2026-10-26.md`, `docs/review/SESSION-2026-10-27.md`, `docs/review/HANDOVER-2026-10-26.md`, `docs/review/HANDOVER-2026-10-27.md`, and `docs/review/HANDOVER-2026-10-27-W16u.md`. Move after confirming their open items are represented in `OPEN-WORK.md` and repairing all references. The current review index already describes these as prior packet/session pointers; keeping only the current handover at the top level would shorten “Start here”.
5. Next, consider `docs/review/HANDOVER-2026-10-28-W16w.md` and `docs/review/HANDOVER-2026-10-29-W16x.md` for the same move once the current pointer no longer needs them in the top-level read order. Keep the latest `HANDOVER-2026-10-31-W16y-c.md` and the immediately previous `HANDOVER-2026-10-30-W16y-b.md` as live pointers for now.

**Do not move these yet:** `docs/review/KT-2026-10-28.md` and `docs/review/OPEN-ITEMS-2026-10-26.md` are dated/closed snapshots, but `OPEN-WORK.md` and other current records still link to them for active owner calls and evidence. `docs/review/OPEN-WORK.md` is the canonical open queue. `docs/review/CLUTTER-2026-10-07.md` still contains unresolved archive/retention plan sections and is referenced by the open-work ledger; resolve/close it before archiving. `docs/review/UNREVIEWED.tsv` is explicitly marked superseded by the 21 Oct audit, but `OPEN-WORK.md` still asks to retire or regenerate it and `selection_writer.py` still reads it through `review_apply.py`; remove that legacy path only as a deliberate separate decision.

The repo’s convention already says closed session records belong in `history/`. Every move needs a reviewed link/index update; Validate’s review-index and relative-link contracts should be run after the move. Do not replace the records with bare redirects.

### P1 — trim repeated living guidance without losing decisions

- Keep distinct canonical roles: `AGENTS.md` = agent contract; `README.md` = owner/user and build guide; `RECOVERY.md` = operational recovery/retention policy; `knowledge/STATE.md` = one current checkpoint plus pointers; `docs/review/README.md` = desk index; dated `KT`/handover/session documents = immutable evidence.
- `knowledge/STATE.md` is 25,165 bytes and is a long running timeline; `docs/review/KT-2026-10-28.md` is 15,562 bytes and repeats current owner/device rules and packet chronology that are also summarized in STATE and newer handovers. Keep the dated KT as evidence, but reduce STATE’s older detailed sections to short pointers and move closed checkpoints into its existing archive rather than repeating the narrative.
- README/AGENTS/KT overlap in build gates, owner approval, safe patch selection, and evidence states. A normalized paragraph comparison found no verbatim long-block duplicates across the four named files, so this is a merge-by-reference recommendation, not a claim that they are copy/pasted. Keep the audience-specific contract in AGENTS; remove duplicated current-state prose from dated handovers when the source-of-truth is already linked.
- `knowledge/README.md` has 0 Markdown inline inbound links; `AGENTS.md` names it as plain text. Make the existing reference clickable or link it from the root index so owners can discover the knowledge navigation page.
- `docs/review/README.md` is an 18,648-byte index for a 93-Markdown-file review tree. Keep it, but simplify the top-level “Start here” list to the current pointer, current queue, and a few active decisions; send closed items to the `history/README.md` index.

### P1 — remove only files proven unused; retain intentional archives

**Unreferenced patch directory:** `src/etc/orphans.sh` reports exactly one unreferenced non-attic directory: `src/patches/telegram-hushtelegram`, holding 62 include-list entries. Leave it. `src/targets.json` explicitly says these HushTelegram selection files are kept unreferenced on purpose; the current Telegram watch row does not authorize building them. `src/etc/cleanup_guard.md` says a populated unreferenced selection directory is reported, not deleted, and `AGENTS.md` protects the attic. The seven lists already under `src/patches/_attic/` are intentional archives.

**Options files:** there are 27 `src/options/*.json` files; 24 option names are referenced by a target candidate, counting disabled CCleaner. `src/options/hosts.txt` is a referenced Adobo resource and must stay. These two JSONs have no target option reference or code caller and are good delete candidates:

| Delete candidate | Evidence it is unused | Restore point |
|---|---|---|
| `src/options/arandomhooman.json` (2 bytes) | No `options` value in any target, including disabled targets; no caller found. | `18211bc29a811bb275746da993c57b4fadd5187e` (last-touch commit; `git show <sha>:src/options/arandomhooman.json > src/options/arandomhooman.json`) |
| `src/options/bufferk.json` (2 bytes) | No target points to this file. The configured Truecaller `bufferk` fallback uses `options: combo`, so delete only `bufferk.json`, not `combo.json` or the provider. | `18211bc29a811bb275746da993c57b4fadd5187e` (`git show <sha>:src/options/bufferk.json > src/options/bufferk.json`) |

`src/options/hushtelegram.json` (3 bytes) is not read by any current target, but leave it for now: the target note deliberately retains HushTelegram’s old selection files and the source is still on the watch list. If the owner later removes that preserved set, its restore point is `ee9b761abafab7a1b376a6207eac0f32a84790f8`.

**Provider baseline:** `provider_watch.inventory(targets, watch_sources=True)` expects 35 baselines; all 35 exist, plus one stale file. `docs/review/providers/hushtelegram-org.telegram.messenger.names` is not a current inventory key; it is byte-for-byte identical (same SHA-256 `7698464e…c9a894`) to the current watched-source baseline `docs/review/providers/extra-sysadmindoc-hushtelegram-org.telegram.messenger.names`. The HushTelegram watch row uses the `extra-sysadmindoc-…` key, so keep that file and delete only the duplicate no-prefix baseline. Restore point for the duplicate is `36ef8c7cc8ac2678e885746b4e1251896a01003b` (`git show <sha>:docs/review/providers/hushtelegram-org.telegram.messenger.names > docs/review/providers/hushtelegram-org.telegram.messenger.names`).

**Script audit — no delete justified after reading:** the caller grep covered workflows, tests, and other source scripts; every apparent no-basename-hit was read rather than labeled dead. `source_pilot.py` is imported by `tests/original_variant_contracts.py`; `community_model.py` is imported by Community watch and tests; `decisions.py` is imported by Selection watch and Needs you. `classify.py` is manually invokable and `docs/review/LEADS-2026-10-08.md` explicitly says “Keep”; `namecheck.sh` calls itself a kept entry point; `onboard_scout.py` is a manual leads tool cited by the W17 plan; `review_full.py` and `review_sheet.py` generate sheets still consumed by `selection_writer.py`, and `docs/review/history/REMOVED-2026-10.md` explicitly says the full/unreviewed modes remain. Keep these. Do not repeat the earlier mistake of deleting a script based only on a caller grep.

### P2 — workflows: all 22 local workflows are purposeful; two labels/descriptions need cleanup

Schedules are listed in `.github/workflows/` UTC and `docs/SCHEDULES.md` IST. The “last observed” column comes only from the supplied status snapshot (`generated_at` 2026-10-30T20:50:28Z); it is not a live GitHub read.

| Workflow | Triggers / schedule | Last purpose (status snapshot / workflow description) | Last observed |
|---|---|---|---|
| `.github/workflows/add-target.yml` — Add target | `workflow_dispatch` | Add/change/disable/remove a target; opens PR. | 2026-10-25 success |
| `.github/workflows/agent-watch.yml` — Provider watch | Monday 06:37 UTC; dispatch | Observe configured provider patch-name changes. | 2026-10-28 success |
| `.github/workflows/batch-patch.yml` — Batch Patch | `workflow_dispatch` | Build an explicit target set. | 2026-10-28 success |
| `.github/workflows/ci.yml` — Check new patch | Daily 12:23 UTC full run; daily 00:23 UTC poll-only; dispatch | Poll providers and build changed apps. | 2026-10-30 failure (Reddit publish correctly refused an older app version) |
| `.github/workflows/community-watch.yml` — Community watch | Monday 03:13 UTC; dispatch | Compare the community patch index for configured apps. | 2026-10-28 success |
| `.github/workflows/council.yml` — Council | PR opened/synchronized/reopened/ready; daily 03:17 and 15:17 UTC; dispatch | Scheduled audit/triage and PR review. | 2026-10-30 success |
| `.github/workflows/explore.yml` — Explore patches | `workflow_dispatch` | List patch names offered by a provider. | 2026-10-25 success |
| `.github/workflows/keepalive.yml` — Keepalive | `workflow_dispatch` only | Manual fallback for GitHub scheduled-workflow pausing. | 2026-10-01 success (last observed event was an older schedule) |
| `.github/workflows/manual-patch.yml` — Manual Patch | `workflow_dispatch`; reusable `workflow_call` | Build one target; shared implementation for CI/batch. | 2026-10-30 success |
| `.github/workflows/mcp-scout.yml` — MCP scout | `workflow_dispatch` | Read-only manual discovery for owner review. | 2026-10-27 success |
| `.github/workflows/needs-you.yml` — Needs you | Daily 04:59 UTC; dispatch; `issue_comment` created | Merge five watch reports into one owner-facing issue and record owner choices. | 2026-10-30 success |
| `.github/workflows/notify-failure.yml` — Notify on failure | Reusable `workflow_call` from Status | Open/close one failure issue per upstream automation. | 2026-10-25 success |
| `.github/workflows/onboard-review.yml` — Onboarding review | Target/patch/options/onboarding PR paths; dispatch | Deterministic onboarding record plus agent review. | 2026-10-28 success |
| `.github/workflows/pin-check.yml` — Weekly pin store check | `workflow_dispatch` only | Manual report-only exact store-pin check. | 2026-10-30 success |
| `.github/workflows/qualify-baselines.yml` — Qualify published shadow baselines | `workflow_run` after CI/manual/batch completions, main only | Qualify evidence after a successful whole build run. | 2026-10-30 skipped (“nothing to do”) |
| `.github/workflows/retention.yml` — Retention preview | Monday 03:31 UTC; dispatch | Weekly preview, owner-confirmed apply. | No run recorded in supplied snapshot |
| `.github/workflows/rule-merge.yml` — Rule merge | Daily 04:07 and 16:07 UTC; dispatch | Merge only green Selection-watch rule PRs. | 2026-10-30 success |
| `.github/workflows/selection-watch.yml` — Selection watch | Daily 02:11 UTC; dispatch | Remove vanished patch names, stage new names for review, digest providers. | 2026-10-30 success |
| `.github/workflows/status.yml` — Status page data | Selected main `workflow_run`s; daily 02:53 UTC; dispatch | Refresh Pages status; contains Notify and cache-prune jobs. | 2026-10-30 success |
| `.github/workflows/tooling-watch.yml` — Tooling watch | Daily 04:29 UTC; dispatch | Check pinned build-tool releases and open update PRs. | 2026-10-30 success |
| `.github/workflows/validate.yml` — Validate | PR; main push for selected paths; dispatch | Test targets, scripts, workflows, pages, generated docs and regressions. | 2026-10-30 success |
| `.github/workflows/watch.yml` — Nightly watch | Daily 01:41 UTC; dispatch | Full repository/provider report. | 2026-10-30 success |

No workflow is obsolete on repo evidence. Apparent overlaps are deliberate: CI and Batch call the reusable Manual Patch implementation; Status contains Notify and cache pruning; Validate and Onboarding review are distinct required PR checks; Provider watch, Selection watch, Community watch, and Nightly watch observe different surfaces. Main-writer concurrency comments explicitly coordinate Keepalive/Community/Selection. The status snapshot also has four non-file records (`codeql`, `dependabot-updates`, `update-graph`, `pages-build-deployment`); these have no corresponding local YAML and are not extra repo workflows to delete.

Two clarity fixes:

- `pin-check.yml` is titled “Weekly pin store check” but has no `schedule` trigger; its comment and schedule page correctly describe a manual report-only probe. Rename it to “Pin store check (manual)” if that is still the intent, or add a reviewed schedule only after the live-check decision.
- `src/etc/status.py` still describes `ci.yml` as “one full run a day, three quick checks.” The checked-in CI file and generated `docs/SCHEDULES.md` have one full + one poll-only scheduled run, not three quick checks. Update that purpose string and regenerate the next status artifact. The old `docs/review/AUDIT-ACTIONS-2026-10-25.md` is a dated count of the former schedule and should remain historical, not be silently edited.

### Generated files — all requested outputs are in sync

Read-only `--check` runs all succeeded:

| Output | Generator / source | Check |
|---|---|---|
| `README.md` generated state block | `src/etc/readmegen.py` from `src/targets.json` and CI crons | `python3 src/etc/readmegen.py --check` — current |
| `CREDITS.md` | `src/etc/credits.py` from enabled targets plus fixed tooling credits | `python3 src/etc/credits.py --check` — current (45 credited rows) |
| `docs/SCHEDULES.md` | `src/etc/schedules.py` from all workflow crons and `src/etc/status.py` purposes | `python3 src/etc/schedules.py --check` — current (14 schedules) |
| `docs/index.html` catalog and `portal.js` cache-busting hash | `src/etc/pagegen.py` from `src/targets.json` and exact bytes of `docs/portal.js` | `python3 src/etc/pagegen.py --check` — current; `docs/portal.js` SHA-256 is `a3a12c0594785834bfc005b00c99007a1e8d3bede28f583986357292858b2cc9`, and the HTML query string matches. |

### Release shelf and other remote state

The status snapshot has 17 apps, each with one latest known release, and no full release inventory. The local clone has 43 local tags, all matching build-tag syntax; tags per prefix are AdGuard 2, Amazon Music 2, Edge 1, ES File 3, Facebook 3, Photos 2, Hotstar 1, Instagram 3, Key Mapper 1, LinkedIn 1, MX Player 3, Prime Video 2, Reddit 4, Truecaller 5, Telegram 2, YouTube 4, YouTube Music 4. The local refs suggest more than the three-release keep threshold for Reddit/Truecaller/YouTube/YouTube Music, but tag refs are not a complete release/deployment/cache API inventory and the script’s ordering is by live publication time, with fallback, age, retired-build and open-PR protections.

**Exact first-apply deletion list is not derivable from `status.json`.** That file exposes only the latest release for each of 17 apps; it has no older releases/assets, release ids, full remote tags, Pages deployment records, or cache list. Local tag refs do not establish the remote release inventory or publication timestamps. No live GitHub API data was available to verify releases, tags, deployments, PRs/branches, or caches. Therefore exact delete counts, asset bytes, deployment IDs, and branch names remain unknown until the scheduled preview runs. The first apply is permitted only after the date gate (after 2026-11-02) and after the owner reviews that preview’s exact token.

- **Old releases/tags:** let `cleanup.py` build the preview. It keeps three releases/app and associated protections; removes corresponding release tags and orphan build tags, not arbitrary non-build tags. `src/etc/retired-builds.json` contains one Reddit 2026.42.0 retirement rule; the status snapshot’s latest Reddit release is 2026.41.0, but that does not prove whether the retired release still exists.
- **Pages deployments:** older than the newest three records are candidates. The workflow waits for the latest Pages deployment to settle; cleanup marks each chosen deployment inactive before deleting the record. The saved `DEPLOYMENTS-2026-10-09T135307Z.tsv` is a historical export, not current inventory.
- **Caches:** these are not part of `cleanup.py` or the retention token. `status.yml` separately runs `src/etc/cache_prune.py --apply` with workflow `github.token` and `actions: write`; it preserves the newest cache per conservative key prefix and prunes only non-newest caches last accessed >7 days ago and created >24 hours ago. That is automatic, not owner-token-gated. If the owner’s requirement is that *all* deletion be owner-confirmed, make the cache job dry-run/owner-dispatch-only before any extra pruning; do not run a separate manual cache delete from this survey.
- **Artifacts/runs:** release retention explicitly excludes Actions runs/artifacts. Their workflows set artifact `retention-days` (typically 1–30 days); this survey did not enumerate live artifacts. Keep the existing expiry policy unless the owner separately approves an artifact/run cleanup.

### Safe in one housekeeping packet

A narrow PR with no behavior change could: (1) delete only `src/options/arandomhooman.json`, `src/options/bufferk.json`, and the byte-identical, non-inventory `docs/review/providers/hushtelegram-org.telegram.messenger.names` duplicate, preserving the restore SHAs above; (2) correct the `RECOVERY.md` / `cleanup.py` policy prose to the actual 3-release / 3-deployment / 7-day guards; and (3) fix the stale `ci.yml` purpose string. Do not include the intentional Telegram selection directory, HushTelegram option file, any scripts, or any history moves. Run the focused option/provider/cleanup/status contracts and the full Validate suite; use a separate PR for mass history moves because they need careful link and index repairs.

## Per-file Markdown inventory

`Inbound` is explicit relative inline-Markdown links from the 148-file survey set to that exact file. A zero count is not a deletion signal: archives, root conventions and manually invoked docs can be intentional.

| Path | Size (bytes) | Last commit date | Inbound links |
|---|---:|---|---:|
| `AGENTS.md` | 5,473 | 2026-10-25 | 1 |
| `CHANGELOG.md` | 33,180 | 2026-10-23 | 0 |
| `CREDITS.md` | 6,329 | 2026-10-30 | 1 |
| `README.md` | 9,674 | 2026-10-30 | 2 |
| `RECOVERY.md` | 7,725 | 2026-10-26 | 5 |
| `SECURITY.md` | 5,247 | 2026-10-27 | 2 |
| `docs/APPS.md` | 3,250 | 2026-10-26 | 2 |
| `docs/SCHEDULES.md` | 2,493 | 2026-10-30 | 4 |
| `docs/companions.md` | 12,581 | 2026-10-25 | 2 |
| `docs/council/AGENT-SPEC.md` | 3,937 | 2026-10-17 | 2 |
| `docs/council/ASK.md` | 1,564 | 2026-09-29 | 0 |
| `docs/council/AUDIT.md` | 2,434 | 2026-10-11 | 1 |
| `docs/council/LESSONS.md` | 40,709 | 2026-10-27 | 6 |
| `docs/council/ONBOARD.md` | 3,403 | 2026-10-25 | 0 |
| `docs/council/OWNER.md` | 2,797 | 2026-10-26 | 0 |
| `docs/council/PERSONAS.md` | 2,744 | 2026-10-26 | 1 |
| `docs/council/PROMPT.md` | 1,752 | 2026-09-27 | 0 |
| `docs/council/PROVIDERS.md` | 9,572 | 2026-10-26 | 4 |
| `docs/council/README.md` | 9,124 | 2026-10-26 | 1 |
| `docs/council/REVIEW.md` | 1,805 | 2026-10-07 | 0 |
| `docs/council/RUNNERS.md` | 3,033 | 2026-10-26 | 5 |
| `docs/council/SETUP.md` | 8,593 | 2026-10-26 | 3 |
| `docs/council/TRIAGE.md` | 1,236 | 2026-10-07 | 1 |
| `docs/council/checklists/MECHANIC.md` | 910 | 2026-10-22 | 0 |
| `docs/council/checklists/WARDEN.md` | 1,976 | 2026-10-22 | 0 |
| `docs/guide.md` | 12,899 | 2026-10-30 | 6 |
| `docs/review/APK-SOURCE-ADMISSION-PHOTOS-2026-09-26.md` | 3,516 | 2026-09-26 | 3 |
| `docs/review/APK-SOURCE-ADMISSIONS-2026-09-26.md` | 5,853 | 2026-09-26 | 4 |
| `docs/review/APK-SOURCE-FALLBACKS-2026-09-26.md` | 10,668 | 2026-09-26 | 1 |
| `docs/review/AUDIT-2026-10-21.md` | 3,910 | 2026-10-21 | 3 |
| `docs/review/AUDIT-2026-10-26.md` | 4,033 | 2026-10-26 | 8 |
| `docs/review/AUDIT-5S-2026-09-27.md` | 5,764 | 2026-10-07 | 5 |
| `docs/review/AUDIT-ACTIONS-2026-10-25.md` | 11,353 | 2026-10-26 | 2 |
| `docs/review/AUDIT-AGENTS-2026-10-25.md` | 22,062 | 2026-10-26 | 2 |
| `docs/review/AUDIT-COUNCIL-2026-10-06.md` | 16,176 | 2026-10-07 | 4 |
| `docs/review/AUDIT-MICRO-2026-09-27.md` | 6,414 | 2026-09-27 | 2 |
| `docs/review/AUDIT-W16.md` | 8,757 | 2026-10-24 | 3 |
| `docs/review/CLUTTER-2026-10-07.md` | 15,962 | 2026-10-11 | 4 |
| `docs/review/CORRECTION-2026-10-27-W16t.md` | 655 | 2026-10-27 | 1 |
| `docs/review/DECISION-REVIEW-2026-10-29.md` | 30,156 | 2026-10-29 | 2 |
| `docs/review/DECISIONS-2026-10-30.md` | 3,520 | 2026-10-30 | 3 |
| `docs/review/FACEBOOK-580-2026-09-29.md` | 4,912 | 2026-10-06 | 6 |
| `docs/review/HANDOVER-2026-10-26.md` | 12,260 | 2026-10-26 | 4 |
| `docs/review/HANDOVER-2026-10-27-W16u.md` | 5,305 | 2026-10-27 | 3 |
| `docs/review/HANDOVER-2026-10-27.md` | 8,187 | 2026-10-28 | 2 |
| `docs/review/HANDOVER-2026-10-28-W16w.md` | 8,715 | 2026-10-28 | 3 |
| `docs/review/HANDOVER-2026-10-29-W16x.md` | 6,559 | 2026-10-29 | 3 |
| `docs/review/HANDOVER-2026-10-30-W16y-b.md` | 4,940 | 2026-10-30 | 3 |
| `docs/review/HANDOVER-2026-10-31-W16y-c.md` | 3,726 | 2026-10-30 | 3 |
| `docs/review/HISTORY-AUDIT-2026-10-21.md` | 4,062 | 2026-10-21 | 4 |
| `docs/review/ICON-PROVENANCE.md` | 11,671 | 2026-10-29 | 2 |
| `docs/review/KT-2026-10-28.md` | 15,562 | 2026-10-30 | 8 |
| `docs/review/LEADS-2026-10-08.md` | 5,094 | 2026-10-08 | 3 |
| `docs/review/MCP-PLAN.md` | 12,214 | 2026-10-27 | 4 |
| `docs/review/OBTAINIUM-SIGNER-2026-10-27.md` | 4,748 | 2026-10-30 | 4 |
| `docs/review/OPEN-ITEMS-2026-10-26.md` | 6,475 | 2026-10-26 | 16 |
| `docs/review/OPEN-WORK.md` | 16,495 | 2026-10-30 | 26 |
| `docs/review/OUTSIDE-REPOS-2026-10-22.md` | 3,919 | 2026-10-22 | 3 |
| `docs/review/PLAN-2026-10-26.md` | 14,063 | 2026-10-26 | 2 |
| `docs/review/PROVIDER-DELTAS-2026-09.md` | 4,312 | 2026-10-21 | 3 |
| `docs/review/PROVIDERS-2026-10-09.md` | 9,819 | 2026-10-09 | 4 |
| `docs/review/README.md` | 18,648 | 2026-10-30 | 3 |
| `docs/review/REPORT-STYLE.md` | 2,318 | 2026-10-23 | 2 |
| `docs/review/RESOURCE-DECISION-2026-09-19.md` | 3,686 | 2026-09-21 | 2 |
| `docs/review/REVIEW-METHOD.md` | 9,009 | 2026-10-26 | 6 |
| `docs/review/SESSION-2026-10-25.md` | 10,269 | 2026-10-26 | 2 |
| `docs/review/SESSION-2026-10-26.md` | 11,368 | 2026-10-28 | 5 |
| `docs/review/SESSION-2026-10-27.md` | 13,051 | 2026-10-28 | 4 |
| `docs/review/SIGNING-SPLIT.md` | 2,055 | 2026-10-22 | 12 |
| `docs/review/SOURCE-CHAIN-2026-10-06.md` | 2,621 | 2026-10-06 | 2 |
| `docs/review/TELEGRAM-SURVEY-2026-10-30.md` | 19,168 | 2026-10-30 | 3 |
| `docs/review/W15G-MAP.md` | 30,422 | 2026-10-27 | 3 |
| `docs/review/W16-WATCHES.md` | 2,408 | 2026-10-23 | 3 |
| `docs/review/W17-BRIEF.md` | 6,130 | 2026-10-26 | 10 |
| `docs/review/W17A-MAP.md` | 42,006 | 2026-10-28 | 2 |
| `docs/review/YTMUSIC-2026-10-06.md` | 4,126 | 2026-10-06 | 2 |
| `docs/review/controllers/README.md` | 12,155 | 2026-10-27 | 6 |
| `docs/review/history/AGENT-2026-09.md` | 4,317 | 2026-10-09 | 1 |
| `docs/review/history/AGENT-SETUP-2026-09.md` | 4,163 | 2026-10-09 | 1 |
| `docs/review/history/AUDIT-2026-09-07.md` | 5,284 | 2026-10-07 | 2 |
| `docs/review/history/AUDIT-2026-09-26.md` | 6,081 | 2026-10-09 | 2 |
| `docs/review/history/CANDIDATES-2026-10-08.md` | 423 | 2026-10-30 | 6 |
| `docs/review/history/CLOUDSHELL-CLEANUP-2026-10-29.md` | 2,129 | 2026-10-29 | 2 |
| `docs/review/history/HANDOVER-2026-09-26.md` | 4,998 | 2026-10-07 | 4 |
| `docs/review/history/HANDOVER-2026-10-23.md` | 5,499 | 2026-10-26 | 2 |
| `docs/review/history/OPEN-WORK-ARCHIVE-2026-10.md` | 82,298 | 2026-10-30 | 3 |
| `docs/review/history/README.md` | 3,143 | 2026-10-30 | 2 |
| `docs/review/history/REMOVED-2026-10.md` | 2,370 | 2026-10-30 | 3 |
| `docs/review/history/REPORT-2026-09-07.md` | 4,026 | 2026-10-09 | 2 |
| `docs/review/history/SESSION-2026-09-06.md` | 6,649 | 2026-10-07 | 2 |
| `docs/review/history/SESSION-2026-09-29.md` | 5,773 | 2026-10-07 | 3 |
| `docs/review/history/SESSION-2026-10-07.md` | 5,642 | 2026-10-24 | 3 |
| `docs/review/history/SESSION-2026-10-08.md` | 12,308 | 2026-10-30 | 4 |
| `docs/review/history/SESSION-2026-10-09.md` | 20,338 | 2026-10-24 | 10 |
| `docs/review/history/SESSION-2026-10-10.md` | 9,896 | 2026-10-24 | 3 |
| `docs/review/history/SESSION-2026-10-11.md` | 6,865 | 2026-10-24 | 3 |
| `docs/review/history/SESSION-2026-10-17.md` | 6,877 | 2026-10-26 | 4 |
| `docs/review/history/SESSION-2026-10-20.md` | 7,825 | 2026-10-24 | 3 |
| `docs/review/history/SESSION-2026-10-21.md` | 8,468 | 2026-10-24 | 4 |
| `docs/review/history/SESSION-2026-10-22.md` | 11,361 | 2026-10-24 | 4 |
| `docs/review/history/SESSION-2026-10-23.md` | 3,960 | 2026-10-26 | 3 |
| `docs/review/history/SESSION-2026-10-24.md` | 14,587 | 2026-10-26 | 5 |
| `docs/review/history/W16-BRIEF.md` | 9,616 | 2026-10-26 | 4 |
| `docs/review/history/WIP-W15-2026-10-17.md` | 2,450 | 2026-10-26 | 4 |
| `docs/review/onboarding/README.md` | 2,497 | 2026-10-30 | 0 |
| `docs/review/onboarding/amazonmusic.md` | 3,353 | 2026-10-30 | 1 |
| `docs/review/onboarding/ccleaner.md` | 2,178 | 2026-10-26 | 0 |
| `docs/review/onboarding/esfile.md` | 2,243 | 2026-10-29 | 0 |
| `docs/review/onboarding/facebook.md` | 15,933 | 2026-10-29 | 1 |
| `docs/review/onboarding/hotstar.md` | 1,014 | 2026-10-24 | 0 |
| `docs/review/onboarding/instagram.md` | 27,590 | 2026-10-29 | 2 |
| `docs/review/onboarding/keymapper.md` | 1,023 | 2026-10-25 | 0 |
| `docs/review/onboarding/linkedin.md` | 3,279 | 2026-10-28 | 0 |
| `docs/review/onboarding/mxplayer.md` | 1,908 | 2026-10-29 | 1 |
| `docs/review/onboarding/photos.md` | 2,038 | 2026-10-25 | 0 |
| `docs/review/onboarding/reddit.md` | 6,893 | 2026-10-28 | 1 |
| `docs/review/onboarding/telegram.md` | 14,821 | 2026-10-30 | 1 |
| `docs/review/onboarding/truecaller-combo.md` | 7,397 | 2026-10-28 | 0 |
| `docs/review/retention/README.md` | 2,402 | 2026-10-24 | 0 |
| `knowledge/LESSONS.md` | 13,815 | 2026-10-26 | 3 |
| `knowledge/README.md` | 1,878 | 2026-10-26 | 0 |
| `knowledge/ROADMAP.md` | 3,298 | 2026-10-29 | 2 |
| `knowledge/STATE.md` | 25,165 | 2026-10-30 | 2 |
| `knowledge/WORKING-AGREEMENT.md` | 4,044 | 2026-09-29 | 1 |
| `knowledge/archive/README.md` | 884 | 2026-10-26 | 1 |
| `knowledge/archive/STATE-2026-09-to-2026-10-24.md` | 34,621 | 2026-10-26 | 1 |
| `knowledge/archive/skills/BUILD-CHAIN-AND-GATES.md` | 5,163 | 2026-09-29 | 0 |
| `knowledge/archive/skills/MY-WRONG-CALLS-ON-PATCH-FACTORY.md` | 24,806 | 2026-09-29 | 1 |
| `knowledge/archive/skills/OPEN-WORK-QUEUE.md` | 21,382 | 2026-09-29 | 0 |
| `knowledge/archive/skills/PATCH-FACTORY-BUILDS.md` | 24,294 | 2026-09-29 | 1 |
| `knowledge/archive/skills/PATCH-SAFETY-AND-SELECTION.md` | 5,704 | 2026-09-29 | 0 |
| `knowledge/archive/skills/PROVIDERS-AND-APK-SOURCES.md` | 5,399 | 2026-10-24 | 0 |
| `knowledge/archive/skills/RELEASES-OBTAINIUM-AND-DEVICES.md` | 10,126 | 2026-09-29 | 0 |
| `knowledge/archive/skills/TARGET-SONYLIV.md` | 2,110 | 2026-09-29 | 0 |
| `knowledge/archive/skills/WORKFLOWS-HYGIENE-AND-ENVIRONMENT.md` | 8,382 | 2026-09-29 | 0 |
| `knowledge/handbook/AGENT-PERSONAS.md` | 1,220 | 2026-10-29 | 0 |
| `knowledge/handbook/AGENT-TOOLING.md` | 5,551 | 2026-10-01 | 1 |
| `knowledge/handbook/CI-DIAGNOSIS-AND-INFRASTRUCTURE.md` | 8,192 | 2026-09-29 | 0 |
| `knowledge/handbook/FREE-LLM-AGENTS.md` | 1,860 | 2026-10-07 | 0 |
| `knowledge/handbook/FREE-LLM-APIS-2026-10-v2.md` | 14,887 | 2026-10-29 | 0 |
| `knowledge/handbook/GATES.md` | 4,498 | 2026-09-29 | 0 |
| `knowledge/handbook/JUDGEMENT-AND-SCOPE.md` | 4,697 | 2026-10-27 | 0 |
| `knowledge/handbook/PACKET-LESSONS.md` | 3,466 | 2026-10-23 | 0 |
| `knowledge/handbook/REPO-WRITES-AND-EXECUTORS.md` | 7,358 | 2026-09-29 | 0 |
| `knowledge/handbook/REVIEW-METHOD.md` | 2,666 | 2026-10-26 | 2 |
| `knowledge/handbook/SKILL-MAINTENANCE.md` | 5,497 | 2026-09-29 | 0 |
| `knowledge/handbook/SOLO-REPO-ENGINEERING.md` | 8,921 | 2026-09-29 | 0 |
| `knowledge/handbook/VERIFICATION.md` | 5,037 | 2026-09-29 | 0 |

---

Survey inputs: checkout files only, plus the supplied status snapshot at `(assistant sandbox)`. No API-side shelf deletion preview was generated, and no repo edits were made.
