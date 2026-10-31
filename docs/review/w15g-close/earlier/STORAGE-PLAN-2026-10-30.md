# patch-factory storage plan

**Scope.** Read-only analysis of checkout `f8cdcf9` and the owner’s 30 Oct 2026
snapshot (`artifacts.json`, `caches.json`, `releases.json`, `tags.json`,
`deployments.json`, `branches.json`, `workflows.json`). Sizes below use decimal GB
(`bytes / 1e9`). The artifacts endpoint is explicitly capped at 2,000 rows, so
artifact counts and bytes are lower bounds; releases (43), tags (43), caches (170)
and Pages deployments (13) are complete-looking inventories from the supplied
collection.

## Ranked actions

| Rank | Action | Classification | Expected effect |
|---|---|---|---|
| 1 | Keep release assets, not Actions artifacts, as the phone/Obtainium shelf. Change cleanup to keep three per app, keep three Pages records, and require a preview token plus a minimum release age. | **OWNER-CONFIRM** | Current inventory would delete 5 old releases/tags (~0.503 GB of release assets) and 10 old Pages records once the age guard allows it. |
| 2 | Add a weekly **preview-only** retention workflow that opens/updates an issue. Apply only from an owner-only guarded action/comment with the exact current token; write the existing receipt before deletes. | **OWNER-CONFIRM** | Makes cleanup regular without silently deleting a newly published shelf item. |
| 3 | Keep bulky test APKs for 2–3 days instead of 7 after owner confirms device-test handoff is through Releases. | **OWNER-CONFIRM** | In this snapshot, changing `test-apk-*` from 7 to 2 days would eventually remove about 31.75 GB of rows older than two days (31.75 GB is not an immediate deletion; old artifacts retain their original expiry). A 3-day policy is about 26.82 GB. |
| 4 | Correct cache prefix matching so numeric run IDs are not mistaken for hexadecimal hashes; keep newest cache per semantic prefix, delete only non-newest caches after the existing 7-day-unused + 24-hour-old guard. | **SAFE-AUTO** after tests | The collected inventory has 10 immediately eligible CodeQL rows under this corrected grouping (~0.188 GB); all 170 are currently retained by the current conservative logic. |
| 5 | Delete `app/add-ccleaner-40213413719` after the owner confirms no external checkout depends on it. | **SAFE-AUTO** (owner acknowledgement preferred) | Its head is merged into `main`, the branch is unprotected, and the open-PR snapshot is empty; deleting it loses no commit reachable from `main`. |
| 6 | Do not rewrite `status` or `watch-state` as part of release cleanup. | **SAFE-AUTO** | `status` is already force-published as one file with no history growth. `watch-state` deliberately uses Contents API commits; inspect/compact its history separately with owner approval. |

## 1. Actions artifacts

### Inventory and grouping

The supplied `artifacts.json` has **2,000 non-expired rows**, **0 expired rows**,
and **36,939,048,557 bytes (36.939 GB)**. Because collection is capped, this
means “at least 2,000 and at least 36.939 GB”, not a complete total. All 2,000
rows have explicit expiry durations of 1, 2, 7, 14 or 30 days; **no collected
artifact has the 90-day default**. Therefore the hypothesis that current
90-day-default uploads explain the excess is not supported by this snapshot.
The current checkout also has an explicit `retention-days` on every
`actions/upload-artifact` step. Historical artifacts created by an older
workflow revision could have 90-day expiry, but that cannot be established from
this capped, all-≤30-day sample.

| Name pattern (run/attempt suffix removed) | Rows | Bytes | Observed retention | Producer/upload step |
|---|---:|---:|---:|---|
| `test-apk-*` | 385 | 34.187 GB | 7d | reusable [manual-patch.yml, “Save verified test APK and evidence”](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/manual-patch.yml#L235-L244) |
| `build-evidence-*` | 508 | 0.017 GB | 7d | [manual-patch.yml, “Save build evidence”](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/manual-patch.yml#L203-L211) |
| `shadow-inputs-*` | 520 | 0.003 GB | 507×30d, 13×7d | [manual-patch.yml, shadow comparison](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/manual-patch.yml#L225-L234) |
| `source-inputs-*`, `resolved-inputs-*` | 38 | 2.679 GB | 2d | [ci.yml, resolver uploads](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/ci.yml#L97-L124) |
| observations/reports (`source-observation-*`, `resolved-observation-*`, `*-report`, `shadow-plan`) | 325 | 0.00051 GB | 7d/30d | [ci.yml, observation/report uploads](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/ci.yml#L139-L209) |
| watch/community/selection/tooling/needs/onboarding/council/MCP | 223 | 0.051 GB | mostly 30d; 2 council rows 14d | e.g. [watch.yml](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/watch.yml#L37-L46), [community-watch.yml](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/community-watch.yml#L26-L49) |
| `github-pages` | 1 | 0.00086 GB | 1d | GitHub-managed `pages-build-deployment`, not a checked-in upload step |

The count is high because many matrix/target runs upload an APK plus evidence,
shadow and resolver observations; the **34.187 GB `test-apk-*` family is 92.5%
of the observed bytes**. It is not a 90-day leak: it is a high-rate stream of
large APKs intentionally retained for seven days. The workflow’s reusable
manual-patch job is called by CI for many targets, and manual/packet runs add
more rows. `build-evidence-*` and diagnostic families contribute rows but almost
no bytes.

**Exact current retention settings.** The relevant explicit values are:

* `manual-patch.yml`: build evidence 7d, shadow inputs 7d, test APK 7d.
* `ci.yml`: shadow plan 7d, resolver/source inputs 2d, source/resolved
  observations 7d, dependency/source reports 7d.
* Watch/report workflows: generally 30d; `council.yml` 14d; validation smoke
  artifact 1d.
* There is no `retention-days` change to make for a current 90-day upload: all
  checked-in upload steps already set it. The exact storage change to review is
  `manual-patch.yml` test APK **7 → 2 or 3**, not an attempted 90 → lower change.
  Keep build evidence at 7d unless the owner explicitly accepts losing test
  diagnostics; it is only 17 MB here.

The existing expiry mechanism does not retroactively change already uploaded
artifacts. If the owner wants an immediate one-time reduction, add a separate,
previewed API deletion tool for artifacts older than the chosen age; do not mix
that destructive list into release cleanup. Otherwise the saving arrives as the
new 2/3-day cohort replaces the current seven-day cohort.

## 2. Actions caches

### Inventory and producers

There are **170 caches, 2,866,693,792 bytes (2.867 GB)**:

* `morphe-jar-*`: 23 rows, 0.964 GB. These are saved by the
  `actions/cache` step in [manual-patch.yml](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/manual-patch.yml#L164-L170), keyed by `morphe-jar-${{ hashFiles('src/targets.json') }}`.
  There are 9 exact duplicate keys (9 extra rows, 377,164,274 bytes); duplicate
  saves are concurrent/repeated cache writes, not nine different patcher jars.
* CodeQL’s GitHub-managed dynamic workflow contributes 94 rows (~1.903 GB,
  47 Python and 47 JavaScript). It is listed as
  `dynamic/github-code-scanning/codeql` in `workflows.json`, not as a checked-in
  `actions/cache` step.
* `pf-action-smoke-*`: 53 rows, only 15 KB, saved explicitly by
  `actions/cache/save` in [validate.yml](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/validate.yml#L220-L232).

`src/etc/cache_prune.py` **does run automatically**: [status.yml](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/.github/workflows/status.yml#L91-L108) runs on the daily 02:53 UTC schedule and on eligible workflow-run/manual events, with `actions: write`, and invokes `--apply`.

### What it deletes and the gap

The tool’s intended rule is already “newest by `cache_prefix` stays; a
non-newest row is deletable only when `last_accessed_at` is >7 days old and
`created_at` is >24 hours old”; malformed timestamps are retained. It lists all
cache pages and fails closed on partial/duplicate data. On the supplied snapshot,
that produced **zero candidates**, because the inventory is only about 0–7.2
days old and the conservative prefix grouping protects the newest member of
each prefix.

There is a subtle prefix bug for CodeQL keys: the right-most numeric run ID is
accepted by `_HEX` before the preceding commit hash, so every commit hash is
left as part of a distinct prefix. Thus the tool does not achieve the desired
“newest per semantic key prefix” for CodeQL. Exact change:

1. In [`cache_prune.py`](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/src/etc/cache_prune.py#L19-L50), make all-numeric suffix segments ineligible for `_HEX` (or explicitly skip numeric-only segments while scanning from the right). Then a CodeQL key groups as `…-python-2.27.3` or `…-javascript-2.27.3`, regardless of commit/run suffix.
2. Keep `STALE_DAYS=7` and `FRESH_HOURS=24`; do not delete the newest member, and retain malformed rows.
3. Add tests for numeric run IDs after a commit hash, two CodeQL language groups, exact duplicate keys, newest protection and malformed timestamps. Add a dry-run fixture asserting the deletion byte total.

With that prefix correction, the current snapshot has 10 CodeQL rows already
past the stale threshold and eligible for deletion (~0.188 GB). The eventual
steady-state reclaim is larger, but not safely inferable from this 7-day
snapshot. Cache deletion is rebuildable and does not touch releases, tags or
source, so this is the lowest-risk automatic reclamation.

## 3. Releases, tags and Pages

### Current state and the 29 October preview

The live snapshot has **43 releases / 43 build tags**, with release assets totaling
4,887,391,004 bytes (~4.887 GB; the collection note rounds this to 4.66 GB),
and **13 `github-pages` deployment records**. Releases are grouped by the app
prefix before `-v` (17 app groups in this snapshot). Current counts include:
`tc-combo` 5, `yt-music` 4, `youtube-morphe` 4, `reddit` 4; `es-file`,
`facebook`, `instagram`, `mx-player`, `youtube`-family groups and others have
1–3 as shown by `releases.json`.

The saved 29 October preview at
(assistant sandbox)
would have deleted **17 releases, 17 tags, 6 Pages records and 0 branches**,
while keeping 17 releases (one per app) and five Pages records. It is a preview
only and is stale for today’s inventory; it must not be applied now. The reason
is the current checked-in policy, not the new owner request: `cleanup.py` has
`KEEP = 1` and `KEEP_DEPLOYMENTS = 5`.

Under the requested **keep 3 per app / keep 3 Pages** policy, today’s exact
candidate list is **5 releases + 5 corresponding tags** (~503,188,291 bytes of
release assets):

* `yt-music` 9.42.52 (81.967 MB);
* `youtube-morphe` 21.43.523 from 27 Oct (120.051 MB);
* `tc-combo` two older 26.41.5 builds (109.089 MB each);
* `reddit` 2026.41.0 from 27 Oct (82.992 MB).

Keep the three newest by `published_at`, then `id` as tie-breaker. Current
candidate releases are only 2–3 days old, so a minimum age guard prevents an
accidental early delete; until they pass the guard, keeping >3 is expected.
No release is “lost” while the newest three remain, and GitHub release assets,
not Actions artifacts, are what phones and Obtainium download.

### Existing code and automation

[cleanup.py](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/src/etc/cleanup.py)
currently:

* groups app-build tags with `APP_TAG`, keeps `KEEP=1` newest by publication time,
  removes older/retired releases, removes their matching build tags and orphan
  build tags, and preserves non-build tags;
* keeps newest `KEEP_DEPLOYMENTS=5` Pages records, marks old records inactive,
  then deletes them;
* only deletes merged `packet/` or `dev/` branches with no open PR and head
  reachable from `main`;
* on apply, re-reads all lists, recomputes the same token, writes a detailed
  receipt first, deletes in order, and stops on the first failure.

`cleanup_guard.md` is a source-tree patch/archive guard, not a release retention
policy. `release_tidy.py` edits only repeated prose in release notes; it never
deletes assets, tags or releases. The retention README records prior owner-run
receipts and confirms this was previously a manual owner process. There is **no
checked-in scheduled workflow invoking `cleanup.py`**. The packet controller
contains an owner-side preview/apply hook, but it is not a regular GitHub Actions
schedule and its current template reflects the old one-per-app/five-Page policy.

### Exact change and workflow plan

1. **`src/etc/cleanup.py`**
   * Set `KEEP = 3`, `KEEP_DEPLOYMENTS = 3`.
   * Add `MIN_RELEASE_AGE_DAYS = 7` (owner may choose 14; 7 is the proposed
     weekly safety window). Parse `published_at`, falling back to `created_at`;
     if missing/malformed, retain the release. In `plan`, keep the newest three
     unconditionally and only append an older/retired release to `rel` when its
     publication age is at least the minimum. Report `too-young` in `kept` so the
     preview explains why more than three remain.
   * Pass an explicit `now` into `plan` for deterministic unit tests. The apply
     token still guards live changes; if crossing the age boundary changes the
     list, apply must refuse and require a fresh preview. Never special-case the
     newest release into deletion, even for retired/unknown apps.
   * Update module prose, `show()` (“newest three”, age guard), receipt/preview
     fields and `only_apps()` behavior as needed. Keep the existing full-list,
     environment check, inactive-status, receipt and token logic.
2. **New `.github/workflows/retention.yml`**
   * `schedule`: weekly, e.g. `17 3 * * 1` (03:17 UTC Monday), plus
     `workflow_dispatch`.
   * Preview job checks out `main`, runs `cleanup.py preview --out`, uploads a
     small 30-day preview artifact, and opens/updates one fixed “Retention
     preview” issue containing the printed summary, token, counts and the exact
     owner-only apply instruction. It must never apply from the scheduled path.
   * Apply path accepts the token only from an owner-authored issue command such
     as `/retention apply TOKEN` (or an owner-only manual dispatch input), checks
     the current issue/token and invokes `cleanup.py apply --token TOKEN
     --receipt`. Require `github.actor == github.repository_owner`, exact command
     parsing, `contents: write`, `actions: write`, `issues: write`, and fail
     closed on missing/malformed/stale previews. Upload/copy the receipt into
     `docs/review/retention/` only through a separate owner-approved commit or
     artifact; do not silently push documentation from the destructive job.
   * Gate cleanup on a completed main Pages deployment (or retain a short
     settle/wait step) so a new deployment cannot make the preview stale. This
     preserves the existing W12/L049 lesson.
3. **Tests**
   * Extend `tests/cleanup_contracts.py` for keep-three, keep-three Pages,
     young release retention, missing/bad timestamps, newest-never-delete,
     retired-app age guard, token changes and receipt contents.
   * Add a workflow contract test for schedule vs owner-only apply, fixed issue,
     no apply in preview, exact-token/actor guard, permissions and Pages settle.
   * Run the existing cleanup, publish-guard, workflow and full contract suites;
     retain tests proving `release_notes.publish_guard` refuses a lower-version
     fallback and that release-note tidy does not touch assets.

The relevant existing safety sources are [`cleanup.py`](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/src/etc/cleanup.py),
[`cleanup_guard.md`](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/src/etc/cleanup_guard.md),
[`retention/README.md`](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/docs/review/retention/README.md),
and [`release_notes.py`](https://github.com/govinda-rajulu/patch-factory/blob/f8cdcf9bdb6972137448a16d8fe52a91634899aa/src/build/release_notes.py#L174-L193).

## 4. Stale CCleaner branch

`app/add-ccleaner-40213413719` points to
[`ba349e3`](https://github.com/govinda-rajulu/patch-factory/commit/ba349e3e55b909978995565566a8cce9d7e06bd6),
whose commit author is `github-actions[bot]` and message is “apps: add ccleaner
(5. Add target run 40213413719)”. The local checkout verifies that `ba349e3` is
an ancestor of live `main` (`f8cdcf9`); the branch snapshot says it is
unprotected, and `pulls-open.json` is empty. The merge commit is in main, so the
branch is safe to delete after the owner’s ordinary “no external checkout” check.
It is not currently deleted by `cleanup.py`, because that tool intentionally
handles only merged `packet/` and `dev/` branches, not arbitrary `app/` branches.

## 5. Status/watch-state branch storage

* `status.yml` documents and implements a force-push of only `status.json` to
  `status`; this intentionally has **one commit/no history growth**. Do not
  include it in release cleanup.
* `watch_state.py` limits each allowed file to **2 MiB** and allows only
  `state.json` and `needs-you-decisions.json`, but its Contents API `PUT` creates
  ordinary branch commits. Selection Watch writes `state.json` daily and Needs
  You writes the decision ledger on owner decisions. Thus the live tip is bounded
  per file, while branch history can grow. The supplied branch snapshot has no
  commit count, object size, file listing or history data for `status`/`watch-state`,
  so their current byte growth cannot be quantified without a separate paged Git
  refs/commits/tree inventory.
* Do not “clean” `watch-state` by deleting files or force-pushing without a
  migration plan: it is operational state, not disposable build output. If its
  history becomes material, owner-confirm a compaction procedure that snapshots
  both files, creates a replacement branch at the same tip content, verifies both
  readers, and only then retires old history.

## Bottom line

The dominant excess is **7-day test APK artifacts (~34.187 GB of the observed
36.939 GB)**, not 90-day-default uploads. The existing daily cache job is safe
but too conservative for CodeQL’s numeric run suffix; fix its prefix grouping and
retain its stale/newest guards. For the shelf, implement the requested
three-release/three-Page policy only behind the existing preview-token-receipt
safety model, add a weekly preview issue, and use a seven-day minimum release age.
Do not apply the saved 29 October preview: it is a one-release/five-Page policy
and its token is stale.
