# Closed pull-request audit — govinda-rajulu/patch-factory

## Coverage and method

- **Collection:** all 124 input JSONL records processed; 124 unique PR numbers, no duplicate IDs; source file has 124 lines. The supplied population contains 113 merged and 11 closed-unmerged PRs.
- **Processing:** 124/124 assigned records classified; 0 unreadable records. The 11 unmerged PRs were each checked against comments/replacement PRs; packet bodies/comments were scanned for deferred/follow-up language and cross-checked against the current work ledger and repository tree.
- **Source-type mix:** 109 `govinda-rajulu`, 8 `github-actions[bot]`, 7 `dependabot[bot]`.
- **Important checkout limitation:** the available Git checkout is `packet/w16yc` at `74addf36c4586e8c42a94245380cb146ee40f818` (commit timestamp 2026-10-30 23:00Z); `git branch -a` exposes no `main`/`origin/main`. The supplied PR record says #282 merged at 2026-10-31 02:04:54Z, after that HEAD. Thus the filesystem is useful as the supplied 31 Oct tree snapshot, but this clone cannot independently certify it as the post-#282 main tree. #282 is held as partial/unverified for this reason, not because missing code was demonstrated.
- **Counting:** labels are applied per requested precedence: explicit replacement => `CLOSED-SUPERSEDED`; merged bot-generated adoption/dependency work => `BOT-ROUTINE`; unresolved promised follow-up or unverifiable post-merge scope => `MERGED-PARTIAL`. `CLOSED-LOST` means an unmerged useful owner contribution with no replacement; none was found.

## Counts by class

| Class | Count |
|---|---:|
| MERGED-DONE | 105 |
| MERGED-PARTIAL | 4 |
| CLOSED-SUPERSEDED | 11 |
| CLOSED-LOST | 0 |
| BOT-ROUTINE | 4 |
| **Total** | **124** |

## MERGED-PARTIAL — evidence and next step

### #75 — PotHelper companion tracking

- **Evidence:** PR #75 says PotHelper external tracking is pending artifact/client review. Current `docs/companions.md` lines 71–75 keeps client-consumer, license/source, install-implication, and device-verification gates open; lines 169–174 calls it the next candidate. The tree contains documentation, not an Obtainium integration. `OPEN-WORK.md` has no PotHelper-specific item (while documenting related general evidence/review work). PR #76 reports a reviewed artifact metadata audit, but does not close the client/integration gate.
- **Next:** finish client and native-component/license review, decide whether to add a separate opt-in Obtainium entry, and record/track the decision in `OPEN-WORK.md`.

### #78 — source-preparation live integration evidence

- **Evidence:** PR #78 explicitly says live timing and artifact transport need later integration evidence. The current tree contains `src/build/source_inputs.py`, `src/build/source_report.py`, and the CI report job; the recorded tests are fixture/mocked and do not establish live timing or artifact transport. `OPEN-WORK.md` carries broad F05/F06/input-fingerprint work, but not this concrete integration proof.
- **Next:** execute a bounded real Actions source-preparation/build path and record elapsed time, artifact handoff/identity, target/run evidence, and outcome in the current work ledger.

### #81 — separate-repository documentation migration

- **Evidence:** The main community report/snapshot and notification logic is present in `.github/workflows/community-watch.yml`, `.github/workflows/notify-failure.yml`, and `src/etc/community_watch.py`. The PR body separately says “Separate repo documentation migration remains unapplied.” Its destination and document set are not named. `OPEN-WORK.md` line 84 tracks mirroring generic controller/sandbox and review-method notes into openskip/brain, but the records do not show whether that is this migration.
- **Next:** identify the intended destination/document set; reconcile with the existing cross-repo mirror item and either close it with evidence or add the distinct migration explicitly before a separate docs PR.

### #282 — post-merge Telegram publication / live pin check (not independently judged against main)

- **Evidence:** PR data says merged 31 Oct 02:04:54Z and its body promises a Telegram publish and a post-merge pin-check dispatch. Available `HANDOVER-2026-10-31-W16y-c.md` says the next combo should carry the Telegram publish run and that the pin helper is awaiting its first live read. `OPEN-WORK.md` records post-merge pin-check reading/scheduling but no Telegram publication result. The local HEAD predates the merge and has no main ref; therefore no claim is made that the merged code is absent from actual main.
- **Next:** refresh to the exact post-#282 main commit, verify the merged tree, then inspect the Telegram Batch Patch and pin-check run artifacts and record both results in `OPEN-WORK.md`/`STATE.md`.

## CLOSED-SUPERSEDED — unmerged records

| Closed PR | Replacement | Evidence |
|---:|---|---|
| #39 | #62 | Later merged Dependabot group #62 updates checkout/setup-java/cache/github-script; no independent unique dependency work remains. |
| #53 | #62 | Later merged Dependabot group #62 covers the same action family and adds download-artifact. |
| #103 | #124 | Owner comment explicitly says #124 replaces the same six setup-java workflow bumps and also fixes the composite pin. |
| #185 | #187 | Owner comment: same upload-artifact 7.0.2 and download-artifact 8.0.2 pins applied across 11 workflows in #187. |
| #188 | #193 | Owner comment: setup-java 6.1.0 applied in six workflows and the preparing composite; #193 closes #188. |
| #194 | #204 | Owner comment: setup-python 7.0.0 applied to .github/actions/preparing/action.yml in #204. |
| #202 | #204 / #207 | Owner comment says #204 closes stale branch, corrects reserved Photos AMOLED assignment and onboarding records; corrected Selection rule later merged as #207. |
| #243 | #244 | W16i #244 excludes the three intentionally rejected names and reoffers the other 16; #243 comment says exactly this. |
| #246 | #247 | Owner comment says byte-identical adoption content carried by #247; closed to avoid Rule merge racing it. |
| #274 | #275 | Owner comment says the three HushGram names folded into #275; current include-patches confirms them. |
| #277 | #278 | Owner comment says seven names folded into #278 with onboarding records; W16x packet records fold. |

## Follow-up promises not specifically recorded in OPEN-WORK

- **#75:** PotHelper client/integration gates are tracked in `docs/companions.md`, but not as a PotHelper-specific current OPEN-WORK item; see partial finding above.
- **#78:** live timing/artifact-transport integration evidence is not named in OPEN-WORK; broad F05/F06 wording is not equivalent to evidence that the real workflow has been run.
- **#81:** separate-repository documentation migration is explicitly described as unapplied; possible overlap with the current generic cross-repo mirror task is unclear.
- **#282:** post-merge Telegram publication result is not recorded; post-merge pin-check follow-up is tracked, but outcome is pending/unavailable in this checkout.

## Other checks and items not treated as partial

- **#74:** the safe Reddit probe failure-category change was later retired; `docs/guide.md` says the Reddit page diagnostic was removed on 8 Oct when builds returned to APKPure. It is not a live outstanding follow-up.
- **#163 review comment:** one Council seat offered a low-severity advisory to generalize native version-marker logic for future vendors. The comment calls it a lead, not an owner commitment; current `src/build/native_payloads.py` still has format-specific literal branches. It is not counted as a promised PR scope gap.
- **#47:** approval enforcement is deferred in the body, but the broader effective/default approval audit is represented in OPEN-WORK; the exact YouTube exclusion is present in the current selection and documented.
- **#80/#81 live external runs:** repository source proves scheduled workflow/report logic, not that each external run/readback succeeded. The supplied PR dataset contains no Actions run artifacts. No runtime success is inferred from code alone.
- **No `CLOSED-LOST` PRs found:** all 11 unmerged items are routine dependency/bot adoption changes replaced or carried by later numbered PRs. No unmerged owner-authored patch PR appears in this 124-record set.

See `P.csv` for one row per PR, preserving the supplied `merged` timestamp or `null`, evidence, and next step.
