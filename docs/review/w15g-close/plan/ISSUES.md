# Patch Factory issue / PR audit (partial; 31 Oct 2026 snapshot)

## Coverage and limits

This is a **partial audit, not an all-record CSV**. The CSV contains the eight open issues whose bodies/comments were available in the owner-probe `case-review.json`. It does not silently assign classes to records whose issue/PR bodies could not be read.

- **Assigned target:** every public issue and pull request, open and closed.
- **Listing collection:** GitHub HTML search pages were used as a fallback after both REST API URLs (`/issues?state=all&per_page=100&page=1`, and `/issues`) failed to fetch. Pagination showed 8 open issues; 150 closed issues (six full pages of 25; page 7 confirmed empty); 124 closed PRs (four pages of 25 and one page of 24; page 6 empty); and no open PRs. This accounts for 282 index rows at listing level. The REST API did not provide a machine-readable authoritative total.
- **Record analysis:** 8/282 bodies analyzed against current local repo and review docs. Remaining: 150 closed issue bodies and 124 closed PR bodies (274 records) need retrieval and repo verification. The list views exposed titles, authors and states, and closure/merge day in the rendered rows, but not exact creation timestamps, complete labels, full bodies, or precise closed timestamps. Individual issue/PR detail pages and REST were not readable through the fetch tool. **Those 274 rows are intentionally omitted rather than fabricated.**
- **Open-issue source:** `(assistant sandbox)`, generated `2026-10-31T01:52:37Z`, says 8 open issues, 0 open PRs; includes all 129 comments and marks the comment collection complete for each open issue. Open search page showed the same eight issue IDs. All eight issue bodies and the decision-bearing recent comments were reviewed; the long, repetitive historical comment histories were not reread in full. No issue body was unreadable.
- **Repo evidence:** local clone HEAD `74addf3`; read `docs/review/OPEN-WORK.md` (checkpoint 31 Oct), newest handover `docs/review/HANDOVER-2026-10-31-W16y-c.md`, `src/etc/needs_you.py`, `.github/workflows/needs-you.yml`, and `.github/workflows/notify-failure.yml`.

### Collection / processing accounts

| Account | State | Count/evidence | Remaining |
|---|---|---:|---|
| Collection — list-level inventory | Partial for content; HTML pagination exhausted at list level | 282 listed: 158 issues (8 open + 150 closed), 124 closed PRs; no open PRs | 274 full records: fetch body/comments and exact metadata, then verify against clone |
| Processing — record classification | Partial | 8/282 open issue records classified from their bodies and latest decision-bearing updates; 0 unreadable bodies | 274 closed records not analyzed; additionally, historical comment text on long open threads was not exhaustively reviewed. Fetch exact metadata/bodies, verify closure/duplicate links, and inspect historical comments only where they affect current status |

## Counts by class (verified open subset only)

| Class | Count |
|---|---:|
| BOT-NOISE | 5 |
| OWNER-ACTION | 3 |
| DONE | 0 |
| UNFINISHED | 0 separately classified |
| STALE | 0 |
| DUPLICATE | 0 |

The zeroes are **not** findings about the closed population. Items whose bodies were not available have no audited class. Historical comments in the long open watch threads were not exhaustively reread; classification relies on each body and the most recent decision-bearing updates. #280 is unresolved but categorized OWNER-ACTION because the next step is a human diagnosis of an unlogged job failure; no code change can be concluded from the evidence.

## Open OWNER-ACTION items

- **[#154 — Council desk](https://github.com/govinda-rajulu/patch-factory/issues/154).** The standing council issue explicitly says comments are advisory, not a merge/build/close trigger. Its model-watch comment reports missing `nvidia/nemotron-3-super-120b-a12b`; `OPEN-WORK.md` says to replace the missing NVIDIA seat model with one available from the live catalogue (a seat keeps two models). **Next:** replace it with a currently served model while preserving two models per seat, then record the Sunday probe result.
- **[#233 — Needs you](https://github.com/govinda-rajulu/patch-factory/issues/233).** The current rendered body says 8 choices wait (2 new providers, 4 generic patches, 2 other items) and documents `take/drop/hold` and group syntax. The 30 Oct comment adds another model/check item; `OPEN-WORK.md` says 28 Oct choices are already in `DECISIONS.json` and the digest should show only new items after merge. **Next:** review the regenerated digest and answer only still-pending IDs/groups; do not repeat decisions already recorded.
- **[#280 — Failing: 2. Check new patch](https://github.com/govinda-rajulu/patch-factory/issues/280).** Run `41103704066`, attempt 1, reports one failed/interrupted job, `build (reddit) / Patch reddit`, job `124239344603`, with “No failing step recorded; inspect startup/cancellation details.” **Next:** inspect the exact job’s startup/cancellation details, then obtain a green main CI run before the notifier closes the standing issue.

## Other open issues in the verified subset

These are standing automated/report threads, not separate owner tickets. Their status is monitored through the issue itself; decisions should be kept in #233 where the system exposes them. No close-out is recommended from the evidence inspected.

- **[#27 — watch: repo and provider status](https://github.com/govinda-rajulu/patch-factory/issues/27): BOT-NOISE.** Recurring nightly status issue (65 comments) with repeated status snapshots, including OK and NEEDS YOU runs. It is an intentional standing monitor, not a one-off stale ticket.
- **[#182 — Selection watch](https://github.com/govinda-rajulu/patch-factory/issues/182): BOT-NOISE.** Recurring provider-selection report; its decision-bearing items are directed to the Needs you mechanism.
- **[#213 — provider watch](https://github.com/govinda-rajulu/patch-factory/issues/213): BOT-NOISE.** Standing provider status/change thread. Its body is an OK/no-action snapshot, while its sole comment later reports two changed/not-read items; keep the follow-up in the digest rather than treating the old body as current.
- **[#218 — Tooling watch](https://github.com/govinda-rajulu/patch-factory/issues/218): BOT-NOISE.** Standing watch; latest comment lists two items for the next packet, while the report says no immediate owner work.
- **[#276 — community: index changed for apps you build](https://github.com/govinda-rajulu/patch-factory/issues/276): BOT-NOISE.** Recurring multi-part community observation; its report says changes are also represented in Needs you. Do not copy all index events into separate owner tickets.

## Proposed close-outs

- **No immediate close-out is recommended among the eight inspected open issues.** #27/#182/#213/#218/#276 are active standing reports, #154 is the advisory Council desk, and #233 carries owner decisions.
- **#280 is a conditional close-out:** close only after a successful later main run for the same workflow (as the existing notifier does); until then its failed job has no recorded step and remains unresolved.
- The 150 closed issues and 124 closed PRs cannot be recommended for any correction/reopen/duplicate-close action until their bodies and final status are read. No closed-item close-outs are claimed.

## Grouping / digest proposal

1. **Build and workflow failures:** keep one standing issue per workflow, not one issue per run. `.github/workflows/notify-failure.yml` already implements this: it groups by workflow, adds exact-attempt evidence as comments, and closes on the next green main run. Keep actual persistent regressions separate only after the failure is reproduced and diagnosed; transient job startup/cancellation reports remain in the standing thread.
2. **Watch streams:** keep one standing report each for Nightly, Provider, Tooling, Selection, Community, and Council. They can retain run snapshots/large evidence in comments/artifacts. Do not open owner tickets for routine “OK”, “changed”, or provider-index events.
3. **Owner choices:** keep one pinned **Needs you** digest for the small actionable set—decide, install, fix, app, FYI—using the current grouped IDs and take/drop/hold syntax. Do not create a parallel template for decisions already collected there.
4. **Separate issue only for durable follow-up:** a verified defect needing a code fix, a phone/install test with a clear acceptance check, or an external/upstream report that requires a distinct evidence trail/owner. Link it from the digest rather than duplicating the same choices in both places.

## Concrete issue-form and label proposal

There is no `.github/ISSUE_TEMPLATE/` directory in the local clone. Add issue forms only for durable tasks that Needs you does not already track:

- **`owner-follow-up.yml` — title:** `Owner action: <verb> <target>`; labels: `owner-action`, `needs-evidence` (add `phone-test` for device validation). Required sections: one-sentence decision/action; why it is needed; exact steps; expected result / acceptance evidence; device/app/version if applicable; related issue/PR/run links; blocker; owner/check-by date. Do not use it for routine watcher choices.
- **`verified-defect.yml` — title:** `Bug: <workflow/app> — <observable symptom>`; labels: `bug`, `verified`, optionally `security` or `release-blocker`. Required sections: expected vs actual; exact run/job/attempt or app/version/device; minimal reproduction; failure evidence/log link with secrets/PII removed; current workaround; repo location suspected; pass condition. Bot failure reports should continue through notify-failure, not this intake form, until reproduced.
- **Labels:** `owner-action` (human decision or step), `needs-evidence` (not ready to close), `phone-test` (device validation), `upstream` (external dependency/report), `verified` (reproduced), `bot-report` (automated standing record), `digest-source` (source whose owner decisions are surfaced in #233), `stale-candidate` (review before closure). Apply sparingly; the inspected open issues currently have no labels, so these would be new triage labels.

These proposals are based on the local files only; no repository changes were made.
