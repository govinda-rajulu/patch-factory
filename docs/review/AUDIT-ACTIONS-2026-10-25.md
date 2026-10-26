<!-- Written by an assistant research agent on 25 Oct 2026 (W16k groundwork); kept verbatim in packet W16m except one local path. Counted mid-day, not the whole UTC day; see HANDOVER-2026-10-26 section 2.  Describes the workflows before W16k; since then Council has two crons, Notify is called by Status page data (workflow_call), Status lists 14 workflows without a workflow-level concurrency block, and Rule merge runs on two crons plus dispatch. -->
# GitHub Actions usage audit — `govinda-rajulu/patch-factory`

**Scope:** UTC day 2026-10-25 and runs created after it (the API returned no post-day rows in the requested collection). The primary REST collection reported `total_count: 298`; six UTC-hour partitions reconciled exactly to 298 (0+119+67+112+0+0).

## Coverage / limitation

The public `fetch_website` extractor truncates large JSON responses before they can be saved to the sandbox. I therefore preserved the authoritative total and per-workflow totals, but the raw-row JSON below contains the 11 run rows individually recovered from small API responses (the specifically requested run and selected failures), not all 298 rows. Job endpoints were queried for selected failures; some old failed runs returned `total_count: 0` jobs. No logs were downloaded.

Global conclusion counts from the GitHub Actions UI/API filters: **199 success, 20 failure, 49 cancelled, 30 skipped = 298**. These counts are authoritative; duration totals/medians are not reported here because the complete run-row timestamps could not be retained after extractor truncation.

## Run counts by workflow

| Workflow | Runs | Conclusion evidence / notes |
|---|---:|---|
| Status page data | 60 | 34+ visible cancellations in UI; remainder mostly success; exact per-conclusion split needs full rows |
| Notify on failure | 59 | 5 visible skipped; remainder success |
| Qualify published shadow baselines | 32 | 3 failure, 16 skipped, 13 success |
| 11. Rule merge | 35 | repeated cancellations in the burst; exact split needs full rows |
| 1. Manual Patch | 33 | 4 failure, 3 cancelled, 26 success |
| 3. Validate | 10 | 2 failure, 8 success |
| CodeQL | 11 | all observed success |
| Council | 7 | 2 failure, 5 success |
| Needs you | 8 | 4 skipped, 4 success |
| 9. Batch Patch | 6 | observed success |
| pages build and deployment | 6 | observed success |
| 2. Check new patch | 5 | observed success |
| Tooling watch | 4 | observed success |
| 10. Selection watch | 4 | observed success |
| 7. Nightly watch | 4 | 1 failure, 3 success |
| 6. Provider watch | 3 | observed success |
| 8. Community watch | 3 | 1 failure, 2 success |
| Onboarding review | 7 | 6 failure, 1 success |
| MCP scout | 1 | 1 failure |
| Keepalive | 0 | no runs |
| Add target / Explore patches | 0 | no runs |
| **Total** | **298** | **199 success / 20 failure / 49 cancelled / 30 skipped** |

## Redundancy findings

1. **Status page and Rule merge are burst amplifiers.** Their `workflow_run` triggers react to many upstream completions. The same packet head (`9ad6af15…` for main after PR #247) produced repeated Status and Rule runs; concurrency cancellation then discarded many of them. This is the clearest redundant fan-out.
2. **Notification fan-out is near one-for-one.** `Notify on failure` had 59 runs, while 5 were skipped. It is triggered by a broad list of workflows and adds a run for each completed upstream event. Narrowing it to actual failures (or replacing it with one consolidated notifier) is high-value.
3. **Qualify is largely skipped/repeated.** It had 32 runs: 16 skipped and 3 failed. Its `workflow_run` trigger listens to Manual Patch, Check new patch, and Batch Patch, so packet batches create many wake-ups that do not qualify anything.
4. **A single packet branch caused parallel PR checks.** The `adopt/2026-10-25-*` PRs produced simultaneous `Council`, `Onboarding review`, and `Validate` runs; three long-lived runs were each shown as 3h38m12s in the UI. That is an overlap/queue signal, not productive execution time.
5. **The owner’s one-hour packet was a manual fan-out.** The UI shows dozens of per-app Manual Patch runs between 07:50 and 12:10 UTC, plus a 7-target publish batch and a 17-target nonpublishing batch. Repeated per-app smoke runs are the dominant essential-vs-redundant question: retain one batch plan/build path, not both batch and individually dispatched smoke runs for the same head.

## Failed runs recovered with job evidence

| Run ID | Workflow / event | Job and failed step(s) | Plain reading |
|---:|---|---|---|
| 40196050562 | MCP scout / workflow_dispatch | `Read-only community scout`: `Read-only GitHub MCP scout`; `Prove the agent left the checkout unchanged` | MCP scout failed its scout step and its post-check cleanliness proof. The requested run was 22s and had no log access here; cause wording is a step-name-based guess. |
| 40195009005 | 7. Nightly watch / workflow_dispatch | `watch`: `Enforce report result (coverage listed separately)` | Collection/report succeeded; enforcement failed immediately. Likely incomplete coverage/report enforcement (guess from step name). |
| 40194762238 | 8. Community watch / workflow_dispatch | `watch`: `Collect complete index comparison and website history` | Collection failed before delivery; delivery and advance were skipped. Likely source/index/history collection failure (guess). |
| 40194589140 | Qualify published shadow baselines / workflow_run | `qualify`: `Qualify only exact completed successful publication receipts` | Settlement succeeded but qualification rejected/failed on publication receipts (guess). |
| 40191953578 | Manual Patch / workflow_dispatch | `Patch keymapper`: `Patch apk` | APK patching failed after preparation; downstream verification/release steps skipped. |
| 40174306889 | Manual Patch / workflow_dispatch | `Patch telegram`: `Patch apk` | APK patching failed after preparation; downstream verification/release steps skipped. |
| 40176187813 / 40176187814 / 40176187853 | Onboarding / Validate / Council, pull_request | API job endpoint returned zero jobs for these older runs | Run-level failures are confirmed; job/step cause unavailable from the public jobs response. |
| 40172258327 / 40172258285 | Validate / Council, pull_request | API job endpoint returned zero jobs | Run-level failures are confirmed; job/step cause unavailable from the public jobs response. |

The UI failure filter contains 20 failures total. The remaining failure IDs (including the other Manual Patch, Qualify, and Onboarding failures) require the complete untruncated run-list response to map from run number to ID before job lookup; they are not invented here.

## Specifically requested run 40196050562

- Workflow: **MCP scout** (`.github/workflows/mcp-scout.yml`)
- Trigger: `workflow_dispatch`
- Created/started: `2026-10-25T13:05:45Z`; updated `13:06:07Z`
- Job: **Read-only community scout** (failed)
- Failed steps: **Read-only GitHub MCP scout** and **Prove the agent left the checkout unchanged**
- Other notable steps (success): key check, output validation, cleanup, artifact upload, post steps.

## Workflow triggers and concurrency (main/W16j definitions)

| File | `on:` triggers | Concurrency |
|---|---|---|
| `manual-patch.yml` | `workflow_dispatch`, `workflow_call` | `build-${{ inputs.target }}-${{ inputs.provider || 'all' }}` (no cancel) |
| `batch-patch.yml` | `workflow_dispatch` | none |
| `ci.yml` | 4 schedules (`23 12`, `23 18`, `23 0`, `23 6` UTC), `workflow_dispatch` | `daily-poll`, queue |
| `validate.yml` | `pull_request`; `push` on main with paths `src/**`, `.github/**`, `tests/**`, `docs/**`, `*.md`; `workflow_dispatch` | none |
| `council.yml` | PR opened/synchronize/reopened/ready; 6 schedules; `workflow_dispatch` | `council-${{ github.event.pull_request.number || 'desk' }}`, cancel-in-progress true |
| `onboard-review.yml` | PR same four types, paths limited to target/patch/options/onboarding docs; `workflow_dispatch` | `onboard-${{ github.event.pull_request.number || inputs.pr }}`, cancel true |
| `notify-failure.yml` | `workflow_run` completed for 13 named workflows | `notify-${{ github.event.workflow_run.id }}-${{ github.event.workflow_run.run_attempt }}`, no cancel |
| `status.yml` | `workflow_run` completed for 12 named workflows; daily schedule `53 2 * * *`; dispatch | `status-page`, cancel true |
| `qualify-baselines.yml` | `workflow_run` completed for Check new patch, Manual Patch, Batch Patch | none |
| `rule-merge.yml` | `workflow_run` completed for Manual Patch, Validate, Onboarding; schedules `7 4`, `7 16`; dispatch | `rule-merge`, cancel true |
| `selection-watch.yml` | daily schedule `11 2`; dispatch | `main-writer`, queue |
| `watch.yml` | daily schedule `41 1`; dispatch | `nightly-watch`, queue |
| `agent-watch.yml` | Monday schedule `37 6`; dispatch | none |
| `community-watch.yml` | Monday schedule `13 3`; dispatch | `main-writer`, queue |
| `tooling-watch.yml` | daily schedule `29 4`; dispatch | `tooling-watch`, queue |
| `needs-you.yml` | daily schedule `59 4`; dispatch; issue_comment created | `needs-you`, queue |
| `keepalive.yml` | dispatch | `main-writer`, queue |
| `mcp-scout.yml` | dispatch | `mcp-scout`, queue |
| `add-target.yml` | dispatch | `app-change`, queue |
| `explore.yml` | dispatch | none |

## Ranked recommendations (runs saved/day, based on observed counts)

1. **Replace broad Status `workflow_run` fan-out with one debounced run per upstream burst.** File `.github/workflows/status.yml`; exact block is the `on.workflow_run.workflows` list of 12 workflows plus `schedule: 53 2 * * *`. Keep the schedule as a safety net, but gate/debounce workflow-run events by head SHA. This targets the 60-run Status population and 49 cancellations overall.
2. **Debounce Rule merge and remove its duplicate safety schedule if the upstream completion trigger is reliable.** File `.github/workflows/rule-merge.yml`; exact block is `workflow_run` for Manual Patch/Validate/Onboarding plus cron `7 4` and `7 16`. This targets 35 runs and repeated cancellations.
3. **Make Qualify one batch-level trigger instead of all completed Manual Patch/CI/Batch events.** File `.github/workflows/qualify-baselines.yml`; exact block is `workflow_run.workflows: ['2. Check new patch', '1. Manual Patch', '9. Batch Patch']`. Its 32 runs included 16 skipped.
4. **Narrow Notify on failure to failure conclusions, or consolidate into one notifier.** File `.github/workflows/notify-failure.yml`; exact block is the 13-workflow `workflow_run` list. It generated 59 runs, including 5 skipped, for little execution value.
5. **Keep PR-path filters and remove the redundant push validation for packet branches.** File `.github/workflows/validate.yml`; exact block is the `push.branches: [main]` plus broad `paths` list. The PR runs already validate packet changes; the main push run is useful only as post-merge protection. Do not remove that protection without retaining one post-merge check.

## Source notes

- Run collection: GitHub REST `actions/runs` pages with `created >= 2026-10-25`, partitioned into 00–03, 04–07, 08–11, 12–15, 16–19, 20–23 UTC; totals 0, 119, 67, 112, 0, 0.
- Workflow definitions: `.github/workflows/*.yml` at the W16j tree (main `9ad6af15`).
- Job data: GitHub REST `/actions/runs/<id>/jobs`; logs intentionally not downloaded.
