# W17a implementation map: owner-only Add app from Pages
Written 26 Oct 2026 by a read-only research agent (Anthropic Claude models) from commit b5a13c4; verify every file:line against the live code before use.

**Evidence checkout:** `a read-only clone`, commit `b5a13c48b96a8a72ab6ad3112e5af4dab49bc4f7`, read-only; focused baseline contracts pass (`PYTHONPATH=tests python3 -m unittest app_contracts onboard_contracts needs_you_contracts rule_merge_contracts provider_watch_contracts variant_ceiling_contracts`: 112 tests). This map is a design/research artifact, not a patch.

**Authority and owner answers.** The W17 brief is [W17-BRIEF.md](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/W17-BRIEF.md); the later checkpoint records the binding answers: Add dispatches both provider-named smokes with no new secret; the owner merges and publishes; new apps use a monogram; no safe name means a disabled target plus a Needs you item; a third provider waits for its own named smoke ([OPEN-WORK.md, item 4](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/OPEN-WORK.md#L27-L30)). “Pages shows it” therefore means the generated catalog/import after the owner’s merge and publish decision, not an automatic merge or release.

## Executive finding and scope

The repository already has a safe, owner-mediated **legacy Add** path, but not the requested one-form discovery path. Existing Add writes repository data and opens a PR; it does not discover providers, query live patch lists, classify names from descriptions, search provider issues, generate a plan, dispatch named smokes, or create a new-app Needs you item. Pages is deliberately read-only and has no Add link or dispatch API. The smallest safe delivery is two reviewed packets:

1. **W17a: discovery, policy, staging, and review data.** Add a reusable provider finder/plan, request validation and identity resolution, live probes and issue evidence, safe-name classification, disabled/pending target support, provider records, monogram default, and a durable Needs you row. Preserve the owner’s final decision and do not auto-merge/publish.
2. **W17b: delivery gates.** Add the Pages link, wire the dispatch form, create the PR, dispatch both exact provider-named nonpublishing smokes with the existing token/secrets (no new secret), make reruns idempotent, and add the end-to-end fake-GitHub rehearsal. The owner still merges and publishes.

W18 should remain separate. It can reuse W17a’s finder/fit evidence, but its combination matrix, version intersection, cost cap, and phone receipts are a different risk surface.

## End-to-end map

### 1. Pages link/form: public read-only surface, owner-only execution

**Existing seam:**

- `docs/index.html:31-39` contains the public masthead, app/import UI, About, and footer. The footer links only Release archive, Workflows, and asset credits; there is no Add app link.
- `docs/portal.js:1-8,53-75` explicitly describes a read-only HTTPS portal, allows only read URLs, omits credentials, and has no workflow-dispatch/write API. `safeLink` (`docs/portal.js:44-52`) only accepts safe GitHub links.
- The app card’s monogram fallback already exists in `docs/portal.js:728-762`: `organizePanel` makes the first character of the rendered name (`:744`), and only replaces it with a local image when `LOGOS` contains the id (`:746`).

**Missing / smallest change:**

- Add an ordinary external `<a>` in the static HTML, preferably About or footer, to `https://github.com/govinda-rajulu/patch-factory/actions/workflows/add-target.yml` (or `/actions/workflows/add-target.yml`). Do **not** make `portal.js` call `/dispatches`, attach `Authorization`, store a token, or accept a token input. The current portal contract intentionally guards the read-only boundary.
- The link may be visible to everyone. GitHub’s workflow-dispatch permission is the owner/write-access gate; the Pages site should document that non-writers can view the form but GitHub refuses execution. Do not claim this refusal is simulated by a local fake.
- Use a stable link test in `tests/portal_contracts.cjs` or a small Pages contract: exact URL, no token/Authorization/dispatch code, and existing read-only source checks remain true.

**Risk:** a tempting in-page form would turn public Pages into a write-capable client and expose a credential. Keep it a link only. Also avoid an untrusted app name becoming HTML: the existing portal uses `textContent` (`el` at `:35`) and generated catalog escaping (`src/etc/pagegen.py:16-20`); retain that boundary.

### 2. Dispatch inputs and owner boundary

**Existing seam:**

- `.github/workflows/add-target.yml:11-71` is `workflow_dispatch` with `action`, required `id`, legacy `package`, `label`, `provider`, `patches`, `source`, `store_url`, `needs_microg`, and public `approve_confirm`.
- Its top-level permissions are `contents: read` (`:9-10`); the `change` job raises to `contents: write`, `pull-requests: write`, and `actions: write` (`:77-84`).
- The workflow sends fields through `env` (`:90-102`) to `src/etc/app.py from-env` (`:104`), rather than interpolating them into a shell command. `src/etc/app.py:519-537` (`from_env`) converts known environment fields to an argv list. Existing tests pin this safe transport in `tests/app_contracts.py:175-187`; `src/etc/nointerp.sh` and `tests/nointerp_contracts.py` cover interpolation.
- `src/etc/app.py:45-48` has current identity/package/provider/store regexes. `cmd_add` validates id/package/provider/label/store at `:332-360`.

**Missing / smallest change:**

- Preserve `action=patch|disable|enable|remove` for existing callers. For `action=add`, accept a new owner-friendly `query` (app label or Android package), optional `store_url`, `group` default `tools`, and optional provider constraint (blank means automatic finder). Keep legacy `id/package/label/patches` only as an explicitly documented compatibility mode; do not let two conflicting identities silently win.
- The lowest-risk shape is either (a) add `mode=discover-add` while retaining legacy `action=add`, or (b) make `query` the required Add input and have the finder derive/confirm id/package/label before any write. A package-shaped query must be validated by `PKG_RX`; a label must resolve uniquely from `bundles.json.store`, an explicitly supplied store URL, or a live provider result. Refuse ambiguous/no-identity requests before writes.
- Add `PF_QUERY`, `PF_GROUP`, `PF_PLAN` (plan path/hash), and an explicit request id to `from_env`; pass `PF_GROUP` because the CLI already supports `--group` (`app.py:554-556`) but current `from_env` does not (`:525-534`). Do not expose an approval checkbox for CONFIRM/paid names in the public form: the owner answers the Needs you item and reruns with the recorded decision.
- Use strict length/control-character/shape validation for every form field, including query, group, provider, and URL. Validate provider as GitHub `OWNER/REPO` (or preserve a deliberate GitLab-extra-only policy); never pass unchecked input to `gh`, Java, a branch name, Markdown, or an issue title.

**Tests to add:** dispatch-input contract (legacy actions preserved; query/group/provider defaults and invalid shapes); `from_env` forwarding for query/group/plan; nointerp fixtures containing shell metacharacters/newlines; collision/ambiguous label cases; no public approval input; Pages link/refusal documentation.

**Risk:** workflow-dispatch visibility is not authentication by the form itself. The authorization comes from GitHub’s write permission plus the job’s `GITHUB_TOKEN`; a fork or arbitrary public caller must not get a write path. The current Add job’s `contents:write`, `pull-requests:write`, and `actions:write` are broad: retain only if needed, and add `issues:write` only if the chosen Needs you delivery design truly requires it.

### 3. Provider discovery: official first, community index, live evidence

**Existing seams:**

- `src/etc/onboard_scout.py:20-69` (`entries`, `mentions`, `patch_names`, `scout`) recursively finds package mentions and names in `src/community/bundles.json`; its own docstring (`:2-10`) correctly says this is a lead list, not proof, and requires provider `list-patches` evidence.
- `src/etc/community_discover.py:23-46` parses the concrete `bundles`, `compatibilities`, and `compatiblePackagesKey` shape, while `src/etc/community_model.py:94-172` (`inventory`) validates and merges duplicate repository records. The checkout’s index currently has `bundles` (284), `compatibilities` (1,488), `store` (1,186), and `featured` (39); the index is metadata, not live admission.
- `src/etc/community_model.py:234-311` (`rank_providers`) is observation-only and ranks an official Morphe owner first, then applicable patch count, current-version support, supported-version count, and freshness. It does not fetch a bundle/list-patches or prove a fitting APK variant.
- `.github/workflows/explore.yml:41-110` is the live probe precedent: validate provider/package, obtain the verified patcher (`:62-72`), fetch the bundle with channel fallback (`:73-94`), run `list-patches --with-packages --with-versions --with-options --filter-package-name` (`:95-110`), and fail on empty/parse mismatch. `src/etc/provider_watch.py:116-161` (`Observer.__call__`, `names_from_output`, `fingerprint`) is the stronger reusable transport/listing implementation: verified bytes, stripped provider environment, timeout, exact `Name:` parsing, duplicate-name collapse.
- `src/build/github_bundle.py:81-142` fetches bounded GitHub releases/assets; `src/build/fetch_bundle.sh` is the existing shell transport. `src/build/variant_pick.py:74-126` (`judge`, `main`) selects arm64/API-ceiling/screen/type-fitting APKMirror rows and exits 4 when none fit. `src/build/version_steps.sh:8-21` bounds step-down (`PF_MAX_STEPS=3`) and uses provider `list-versions`.

**Missing / smallest change:**

- Add `src/etc/provider_finder.py` (standard library, no writes except an explicit plan output) with deterministic functions such as `resolve_request`, `index_candidates`, `probe_provider`, `fit_versions`, `rank_candidates`, `provider_issues`, and `build_plan`.
- Candidate source/order: always inspect official `MorpheApp/morphe-patches` first, then exact package hits from the structured index. Reuse `community_model.inventory` for index validation/duplicate repository merge; do not use `onboard_scout`’s recursive match as final evidence. For each candidate, fetch a verified bundle, run `list-patches` live for the package, obtain the provider’s supported versions, and prove a store variant fits arm64-v8a/API 29 using the existing picker/source path. Keep the exact release/tag/asset/hash/channel and reason for rejection.
- Rank by the brief’s rule: highest app version **actually fitting the phone** first, then most live applicable patches, with official Morphe first as the prescribed first source/order. Make tie-breaking stable by provider identity. “Newest index appUpdates” or `patchCount` alone must never be called a fit. A bundle/list/variant failure is `UNKNOWN`/failed evidence, not “supports all versions.”
- Return at most three roles: `primary`, first `fallback`, and `deferred`. Persist only primary + first fallback as candidates; preserve the third only in the plan/onboarding evidence. The existing build model confirms why: `build_attempts.py:4-17,62-71` treats `candidates` as provider alternatives and `extra_bundles` as bundles combined into one build. A third provider cannot be merely put into `extra_bundles` without changing the shipped combination.
- Important interpretation of the owner answer: the current Manual Patch refuses an unknown provider (`manual-patch.yml:98-105`, then `build_attempts.py:62-71`); therefore the deferred third cannot be smoked by the existing route while absent from the target. W17a should record it as deferred; a later promotion run/PR must wire it as a candidate, then dispatch its own named smoke. Do not silently write an untested third fallback.

**Tests to add:** pure index fixtures (official-first, duplicate repo merge, compatibility reference forms, package/name ambiguity); fake bundle transport/list-patches fixtures (empty/malformed/duplicate output, timeout, provider code without credentials); fit fixtures (newest too high API, same-version alternate store, lower version within max three, no fitting row); deterministic rank/tie tests; cap exactly three and defer third; provider failure reason is retained and never converted to “none.” Existing useful tests are `tests/provider_watch_contracts.py:166-199,273-288`, `tests/variant_ceiling_contracts.py:22-97`, `tests/community_reason_contracts.py`, and `tests/needs_you_contracts.py:396-424` (index/provider ranking, but not the new live finder).

**Risks:** downloaded bundles and patcher output are untrusted data. Keep GitHub credentials out of provider execution as `provider_watch.Observer` does (`:149-159`), use fixed argv (not shell concatenation), cap bytes/time/entries, verify hashes before and after listing, and retain no provider-supplied URLs without allow-listing. A provider issue title/description can contain Markdown, `@mentions`, links, or control characters; escape/limit it before PR records and Needs you.

### 4. Provider issue discovery and onboarding evidence

**Existing seam:**

- No current function searches a provider repository’s open issues for an app/package. `src/etc/provider_watch.py:316-357` edits the patch-factory standing provider-watch issue; that is not provider-repository issue lookup. `src/etc/rule_merge.py:72-79` (`gh_api`) is a generic API reader for this repository’s merge checks, not this feature.
- `src/etc/app.py:152-199` (`provider_text`, `write_record`) writes provider source/channel/bundle/licence text and patch lines, but no `Provider issues:` line.
- `docs/review/onboarding/README.md:26-43` defines the record shape; `src/etc/onboard_check.py:146-238` checks records from the base/head split and enforces exact provider/name mentions, TODO refusal, BANNED, and CONFIRM owner approval.

**Missing / smallest change:**

- In `provider_finder.py`, for each persisted primary/fallback GitHub repo issue-search open issues by both exact package and resolved app label/name. Use the GitHub Issues/Search API with strict repo identity and fixed query construction; retain URL, number/title, matched term, timestamp, and a bounded failure class.
- Extend `write_record` with plan-fed evidence for each provider: exactly one of `Provider issues: none (checked ...)`, `Provider issues: <links>`, or `Provider issues: unable to check (<fixed error class>)`. Never write “none” after timeout, 403/429, malformed API response, non-GitHub provider, or missing identity.
- The record should also name selected/held/BANNED/deferred names, ranked providers, fit/version evidence, and the explicit no-safe-name/disabled reason. Do not let a provider’s own issue decide admission; it is evidence for owner/reviewer only.

**Tests to add:** mocked issue API zero/match/403/429/timeout/malformed; package-vs-label query matching; escaped hostile title/body; record assertion for all three Provider issues states; `onboard_check` accepts a disabled new target with no include names but still requires provider and record; exact provider/name/TODO/BANNED/CONFIRM regressions.

**Permission risk:** add only `issues:read` if the job needs it (public issue search may not require a broad token); never grant provider-repo write, contents write to the downloaded provider, or model/secrets to the finder. `gh api` calls must take arguments, not interpolate query text into shell.

### 5. Safe-name selection and owner memory

**Existing policy and functions:**

- `src/etc/app.py:83-89` reads line-based rules; `screen` at `:126-139` refuses BANNED and refuses CONFIRM unless `approve_confirm` is supplied. This is a hard fail/CLI approval path, not a “hold and continue” classifier.
- `src/patches/BANNED:1-21` contains lowercase substring bans. `src/patches/CONFIRM:1-24` contains owner-call patterns.
- `src/patches/ADOPT.json:2-105` is the real policy: `hold_words` (`:3-35`), `paid_words` (`:37-48`), `paid_ok_targets` (`:50-58`), content/switch/wanted words (`:60-96`), and reserved target/name ownership (`:98-105`).
- `src/etc/selection_watch.py:97-158` (`adopt_policy`, `index_descriptions`, `classify`) is the closest complete classifier. It orders BANNED/CONFIRM, one-bundle duplicate, reserved, missing/universal description, hold words, paid words outside `paid_ok_targets`, and content verbs without an off switch/wanted target. `:167-190` (`peer_names`) detects same-build duplicate ownership. `:456-470` (`remember`) consumes `DECISIONS.json` calls while preserving BANNED/duplicate/reserved/paid hard holds.
- `src/etc/decisions.py:14-52` (`norm`, `load`, `call`, `provider_state`) matches owner decisions per target/name after normalisation. `src/patches/DECISIONS.json:1-3` documents the durable semantics and currently stores `N-xxxxxx` name calls.
- `src/etc/onboard_check.py:87-122` reads paid approvals and owner takes for review policy, while `:199-238` enforces BANNED/CONFIRM on added include names. `src/etc/needs_you.py:61-70` names Needs you groups G2-G7 (no-off-switch, no description, generic, risky, name-only hold, reserved/paid/one-bundle).

**Missing / smallest change:**

- Do not duplicate policy in a new Add script. Extract/reuse a pure classifier from `selection_watch.classify` (or call it through a small stable policy module) and pass live provider descriptions plus same-app provider offers. The Add path must be fail-closed: only clean, described, non-BANNED, non-CONFIRM, non-paid-outside-approved, non-reserved, non-duplicate, non-config-required names become selected.
- Apply `DECISIONS.json` by target id and normalised name. `take` may admit an otherwise policy-held name only where existing semantics permit; it never overrides BANNED, same-build duplicate, reserved, or paid-outside-approval. `drop` stays out and is not asked again. A public Add form must never set `approve_confirm`; a Needs you answer or owner-authored ledger change is the approval source.
- Preserve per-name reason and a stable Needs you id (`N-` six hex is the existing format at `needs_you.py:276-279`/`54-60`). For each provider, selected names go to its include list; BANNED names must not be written at all, and other held names remain only in plan/record/Needs evidence.
- “No safe names” is a first-class outcome: still stage a target/provider record, but write `enabled:false`, `poll:false`, empty include/exclude files, no `exclusive:true`, and a clear pending reason. Do not enable it, build it, or produce a Pages catalog row merely because a provider exists.

**Current-policy caveat:** `app.py:126-139` raises on a BANNED/CONFIRM name, so W17 plan mode must classify/omit rather than pass all names to `screen`. `selection_watch` currently runs against already configured targets and its `Needs you` held rows, not a new Add request. `needs_you.app_items` (`:615-620`) is deliberately retired/no-op for routine “keep building?” questions; it must not be assumed to create an Add item.

**Tests to add:** classifier table covering every `ADOPT.json` rule; BANNED always omitted even if `DECISIONS` says take; CONFIRM/paid/reserved/duplicate/unknown description held; paid target in `paid_ok_targets`; same name from two bundles; normalisation across provider spelling/version suffix; clean names selected; all-held/no-safe result creates disabled target and exactly one stable Needs item; rerun does not duplicate names/items/ledger rows. Existing policy tests: `tests/app_contracts.py:131-141`, `tests/onboard_contracts.py:112-121`, and `tests/needs_you_contracts.py:83-126,194-264`.

### 6. Target record, patch folders, options, store mapping, and plan integrity

**Existing seam:**

- `src/etc/app.py:62-80` reads/writes JSON and preserves fallback formatting; `:298-318` (`apply_store`) validates APKMirror/APKPure URL and writes `src/build/helper/apps.json`.
- `cmd_add` (`src/etc/app.py:332-395`) validates identity, creates the provider patch directory (`:351-355`), writes `src/targets.json` with `enabled`, package, APK/source, SDK ceiling, candidate/provider metadata (`:360-367`), include/exclude files (`:372-374`), options array (`:375-378`), fallback policy (`:380-386`), onboarding record (`:387`), and optional group (`:388-389`). It currently supports only one candidate and has no plan/third/deferred metadata.
- `selection` (`app.py:398-408`) already selects a named candidate or extra bundle; `cmd_patch` (`:411-453`) writes a provider-specific patch list; `cmd_toggle` (`:456-476`) refuses enabling an empty target (`:462-464`).
- Target validation: `src/etc/preflight.py:26-105` skips disabled targets but validates enabled providers, candidates, fallbacks, patch duplicates, options, exclusivity and cross-bundle collisions. `src/build/input_recipe.py:138-199` requires one enabled target, a candidate winner, a store mapping, and fallback policy for builds. Validate’s target/store/extra checks are `.github/workflows/validate.yml:47-150`.
- Existing tests pin writes/disabled behavior in `tests/app_contracts.py:80-129`; `tests/input_recipe_contracts.py`, `tests/fallback_adapter_contracts.py`, `tests/source_fallback_contracts.py`, and `tests/options_contracts.py` cover downstream schemas.

**Missing / smallest change:**

- Add a versioned, bounded plan JSON (e.g. `add-plan.json` in the runner/artifact, not necessarily a committed public file). It must contain request identity, target id/package/label, source URL, candidate identities, roles, exact live evidence/hash, selected names, held reasons/IDs, provider issue states, deferred third, and a plan digest.
- Refactor `cmd_add` into a plan-aware path that atomically verifies package/id/provider identities and plan digest before touching repository files. It must write primary + first fallback under `candidates` (first has `fallback:false`, second `fallback:true`), not use `extra_bundles` for alternatives. Preserve the third only in record/plan evidence until a later promotion PR/smoke.
- Extend `write_record` rather than create a second writer. Keep exact selected names and reasons, provider issue lines, deferred provider, fit evidence, and pending reason. Keep `apps.json` valid even when disabled; the existing Validate warning for a disabled target with no store mapping (`validate.yml:127-143`) is expected, but an eventual enable path must refuse until the store source is complete.
- Make writes atomic/transactional: write candidate files under a temporary staging root, run JSON/schema checks, then replace; on a failed generator/check do not leave a half-written enabled target. Current `cmd_add` mutates several files sequentially and has no rollback.
- For idempotence, derive a stable request key from normalized package/id/provider plan hash and refuse/reuse an existing target/branch/PR rather than creating a second target or duplicate folder. Current `cmd_add` refuses duplicate target ids (`:337-340`) but has no rerun key.

**Schema caution:** README explicitly says a separate cross-consumer schema review is still needed before disabled-target behavior is a complete onboarding contract ([README.md:104-106](https://github.com/govinda-rajulu/patch-factory/blob/main/README.md#L104-L106)). The existing code permits disabled scaffolding in `app.py` tests, but downstream enabled/build assumptions mean W17a must test the whole tree, not only `targets.json`.

### 7. Monogram/logo rule

**Existing seam:**

- `docs/portal.js:19-25` declares local `LOGOS` and groups; `organizePanel` (`:728-762`) uses the first-letter monogram and local `docs/assets/logos/<id>.png` only for admitted IDs.
- `app.py:245-266` (`portal_forget`, `portal_logo`) only adds an id to `LOGOS` when an actual local PNG exists; `portal_logo` never generates artwork. `cmd_add` does not call `portal_logo` (`:387-389` only writes group), so new apps naturally stay monogram-only.
- `docs/review/ICON-PROVENANCE.md` and `tests/portal_contracts.cjs:203-208` require provenance-recorded local PNGs, NOTICE entries, and local file size/type checks. `docs/APPS.md:44-45` says a missing logo displays a letter tile.

**Missing / smallest change:**

- No logo file, `LOGOS` entry, NOTICE line, or network artwork fetch in W17a. Leave new target out of `LOGOS`; ensure target addition cannot infer an icon from `bundles.json.store.iconUrl` or a store page. The existing monogram is the requested output.
- Add a focused test that adding a target with no `docs/assets/logos/<id>.png` does not modify `LOGOS`, does not create a logo file, and renders/falls back to the first label character. A browser/portal contract should verify no remote image URL is introduced.
- A future owner-approved logo is a separate provenance PR: local PNG, source/licence/owner approval/hash in `ICON-PROVENANCE.md` and `NOTICE.txt`, then add to LOGOS. It is not part of Add.

**Risk:** trademark/artwork and remote icon URL leakage; monogram avoids both. A disabled target is not rendered by `pagegen` (`src/etc/pagegen.py:22-40` filters `enabled`), so the monogram is observable once the owner later enables/merges it.

### 8. Named smokes and provider winner gate

**Existing seam:**

- `.github/workflows/manual-patch.yml:1-27` has `publish` (default true), `target`, `provider`, and `keep_going`; the run name includes provider when supplied (`:2`). The build job rejects unknown/disabled targets before secrets/downloads (`:98-109`), then calls `build_attempts.py` (`:175-190`) with `PF_PROVIDER` (`:180`).
- `src/build/build_attempts.py:62-71,142-203` accepts a named candidate and builds exactly it; it emits winner/attempt evidence and no fallback when `PF_PROVIDER` is set. `.github/workflows/manual-patch.yml:244-248` reports a nonpublishing smoke and explicitly says no phone install.
- Current Add dispatches only `validate.yml` and `onboard-review.yml` (`.github/workflows/add-target.yml:106-139`), not Manual Patch. The brief’s L069 rationale is encoded in this workflow and Selection’s equivalent `open_and_check` (`src/etc/selection_watch.py:661-699`): bot-created PRs need explicit Validate/review/smoke dispatches.
- `src/etc/rule_merge.py:86-92,177-189` computes existing Manual Patch titles and requires successful nonpublishing provider runs, but its `decide` path accepts only bot `adopt/` branches (`:101-103`). It does not auto-merge an Add PR, which is consistent with the owner answer.

**Missing / smallest change:**

- After PR creation and head SHA capture, dispatch **two** `manual-patch.yml` runs from the exact PR branch, each with `target=<id>`, `provider=<candidate-name>`, `publish=false`, `keep_going=false`. Dispatch primary and first fallback only. Keep a run identity `(PR head SHA, target, provider, publish=false)` and query it before dispatching so a rerun does not create duplicate smokes.
- Check `gh workflow run` return status. A failed dispatch is an explicit blocked/incomplete result in the Add summary/PR, never green. Do not wait for builds in the Add job; owner inspects the two completed runs before merge. Do not set `keep_going`: W17 acceptance says a named provider must win, not that a fallback diagnostic is advisory.
- Because both runs must be provider-named, pass `provider` even for the primary. Existing `rule_merge.build_title` (`:86-92`) treats a primary run without a provider as `Manual id / publish=false`; W17’s owner-manual gate can use exact named run titles, but if an automated Add readiness checker is added it must accept the named-primary form. Do not broaden auto-merge without a fresh owner decision.
- Require exact provider winner evidence (`ATTEMPTS_OK` and winner equals requested provider), not merely workflow success. If a run accidentally builds a fallback or provider differs, STOP and hold; L098 says a fallback winning a requested primary is not advisory.
- “No new secret” means reuse the existing Manual Patch signing secrets and the existing `github.token`; it does **not** mean expose a new PAT. Current Manual Patch declares `contents:write` and reads signing credentials inside its build steps (`:3-4,185-196`), even for nonpublishing runs. A least-privilege smoke refactor may be safer but is a separate security review; at minimum ensure `publish=false` cannot reach release (`:236-248`) and never dispatch from an untrusted fork.

**Tests to add:** fake `gh` dispatches both named pairs; primary/fallback winner match; provider loses to fallback => STOP; failed dispatch => blocked; duplicate rerun finds existing exact runs; third provider is not dispatched/wired; `publish=false` and no release; no new secret names/PAT; branch head mismatch blocks. Existing build/fallback tests are `tests/rule_merge_contracts.py:247-264`, `tests/build_attempts_contracts.py`, `tests/t1_gate_contracts.py`, and `tests/empty_release_contracts.py`.

### 9. Pull request creation and exact-head checks

**Existing seam:**

- `add-target.yml:106-139` creates branch `app/$PF_ACTION-$PF_ID-$GITHUB_RUN_ID`, refuses workflow-file diffs (`:117-123`), stages `src docs README.md CREDITS.md` (`:124`), commits/pushes, creates the PR (`:129-135`), and warns with a compare link if GitHub refuses PR creation (`:136-139`).
- `src/etc/app.py:587-594` writes a simple summary saying checks/generators passed and instructing owner merge; it has no ranked provider/smoke/issue/Needs details.
- `src/build/input_recipe.py` and build evidence bind later builds to exact source files/target config; `rule_merge` binds checks to exact head (`:100,146-166`).

**Missing / smallest change:**

- Keep the branch/PR creation path but make `pr-body.md` include request identity, package/store, selected/held/BANNED names, provider rank and fit evidence, provider issues, deferred third provider, exact named-smoke pairs and dispatch run URLs/status, and “owner merges and publishes; no auto-merge.” Escape all provider text and cap body size.
- Capture PR number/head SHA only after `gh pr view`; dispatch all checks/smokes with `--ref`/head identity and refuse if the head changes. Preserve the existing “no workflow files staged” guard.
- On GitHub refusing PR creation, report a durable pending request/Needs item and compare URL; do not rerun discovery and push a second branch. Reruns should find existing branch/PR by stable request key.

**Tests to add:** fake GitHub PR refusal/no second branch; exact body fields and safe escaping; head changed between PR and dispatch; staged-file allow-list; rerun idempotence twice; provider-named smoke URLs recorded.

### 10. Onboarding review and merge/publish ownership

**Existing seam:**

- `onboard-review.yml:1-7` names the workflow and separates deterministic base-code record checking from agent review. It intentionally runs the checker from base and keeps model keys away from head; the workflow contract is tested in `tests/onboard_contracts.py:208-228`.
- `src/etc/onboard_check.py:146-238` compares base/head, detects new/disabled-to-enabled targets, new providers, and include additions; requires `docs/review/onboarding/<id>.md`, exact names, no TODO, BANNED refusal and CONFIRM approval. `owner_policy` (`:108-122`) reads paid approvals/takes from base, plus head only in owner-PR mode.
- `onboard_review.py`/council contract then gives the PR a review; README states this is not a build, phone test, merge, or owner approval (`docs/review/onboarding/README.md:7-24`).
- Current Add explicitly dispatches `onboard-review.yml --ref main -f pr=<PR>` at `.github/workflows/add-target.yml:134-135`.

**Missing / smallest change:**

- Keep this two-stage trust split. The Add workflow must dispatch the review for the PR number after creating the PR, and the record must name the provider and every selected include name exactly. For a disabled/no-safe-name target, the record still names the provider and explains no selected name; no `Owner approved:` line is invented.
- If plan records are staged outside normal target files, include a bounded manifest pointer/hash in the onboarding record/PR body, but do not make the head’s plan code the checker authority. Add checker support only for new metadata that is required; do not let the PR rewrite policy.
- W17 owner rule is manual merge and manual publish. No changes to `rule_merge` auto-merge are needed or wanted. Acceptance is all: Validate green, Onboarding review green, **both exact provider-named smokes green with the requested provider winning**, and owner’s explicit merge/publish/phone decision. Publication is a later owner-triggered Manual/Batch Patch action; the Pages catalog/import generator sees a merged enabled target.

**Tests to add:** onboarding disabled target with held-only/no include names; provider issue/deferred lines do not create false include obligations; exact selected names; no-safe name record has no TODO and passes; new fallback candidate is detected; owner policy cannot be rewritten by a non-owner PR.

### 11. Needs you item for no safe names

**Existing seam:**

- `.github/workflows/needs-you.yml` is the scheduled/manual collector and owner-comment route. `src/etc/needs_you.py:240-275` sources report evidence, `:276-290` makes stable ids, `:395-505` renders community provider candidates, `:567-605` renders held Selection names, `:615-620` shows that ordinary app keep-building items were retired, and `:826-960` (`render`, `_grouped`) writes machine-readable item metadata to the standing issue.
- Owner command parsing/authorization is `needs_you.py:699-755` (`parse_decisions`, `authorized_comment`); guarded effects are `:761-807` (`apply_effect`). Existing `take` can dispatch Explore or patch an existing target, but no effect creates/resumes a brand-new Add request. `needs-you.yml` only fetches the five existing watch artifacts; Add is not a source.
- `src/etc/decisions.py` is the durable name decision helper; `needs_you.py:1110-1175` records owner commands/ledger and comments a receipt. Tests cover stable held rows, owner guards, duplicate commands, and existing patch/Explore effects (`tests/needs_you_contracts.py:83-126,194-264`).

**Missing / smallest change:**

- Add an Add-request evidence artifact or checked-in pending record with `{request_id,target,package,label,provider,held_names:[{id,name,reason}],no_safe_names:true,next_action:"owner decision then rerun Add",status}`. It must be bounded, JSON-validated, and immutable/identified by the Add run; do not pass arbitrary issue body as instructions.
- Extend Needs you’s source list/render with `add-target.yml` evidence, or have a dedicated small collector merge Add pending artifacts into the standing issue. Use an `install`/`decide` item with `N-xxxxxx`; group it under G7 or a new explicit “New app waiting for safe names” group. Include the reason and explicit action: owner takes/drops/holds the name, then reruns Add; no automatic enabling from an issue comment.
- Extend `apply_effect` only to record the decision/rerun instruction, not to write `targets.json` from an issue comment. A subsequent owner-only Add rerun consumes `DECISIONS.json`; it verifies the package/provider plan again, then may add safe names. BANNED/reserved/paid hard rules remain non-overridable. The disabled target stays disabled until a later PR and named smokes.
- Make delivery idempotent: same request/name/reason gives one item; a rerun edits the standing issue without duplicate rows; an owner answer is recorded once. If the Add PR is not yet merged, the item must not imply that a main-branch target already exists. The artifact route should survive the PR’s status/branch and have explicit retention/expiry semantics.

**Tests to add:** no-safe Add artifact becomes exactly one Needs item; hostile name/reason escaping; owner-only guard; take/drop/hold records once; rerun twice is quiet/idempotent; no automatic target enable; item disappears/changes only after a new owner-authored rerun or explicit resolution; artifact fetch failure is visible rather than “no pending apps.”

**Risk:** granting Add `issues:write` to edit the standing issue couples PR creation to issue delivery and raises blast radius. Prefer an artifact consumed by the existing guarded Needs you workflow; if direct delivery is chosen, use a separate least-privilege job and fixed safe body generation.

## Proposed packet split and ordered task list

### W17a: discovery and safe staging (review first)

1. **Freeze request/identity contract.** Add query/id/package/label/group/provider precedence, collision rules, length/control-character limits, and stable request key. Acceptance: malformed/ambiguous requests stop before any write; legacy patch/disable/enable/remove behavior unchanged.
2. **Implement provider finder/plan.** Reuse `community_model.inventory`, `provider_watch` transport/parser, `github_bundle`, `variant_pick`, and bounded version-step semantics; add official-first/index candidate collection, live list-patches, fit proof, deterministic rank, top-three roles, exact evidence/hash. Acceptance: fake fixtures show official-first, newest fitting version then patch count, unknown/failing providers held, deterministic top three, third deferred.
3. **Implement policy projection.** Reuse `selection_watch.classify`/`decisions`; classify live names and descriptions; never write BANNED; hold CONFIRM/paid/unknown/reserved/duplicate/no-off-switch names with stable ids. Acceptance: full ADOPT matrix and DECISIONS precedence table passes; all-held yields no selected names.
4. **Make `app.py` plan-aware and transactional.** Add group/plan forwarding; write primary + first fallback candidate records, exact include/exclude/options/store/fallback files, provider issue/deferred/pending record, and disabled no-safe target. Acceptance: `preflight`, `bancheck`, `quarantine`, generator checks, `onboard_check` all pass in synthetic trees; no partial writes on plan mismatch; rerun is no-op/refuses duplicate.
5. **Wire onboarding record evidence.** Extend `write_record` for provider issues, rank/fit, held/deferred/no-safe state. Acceptance: base/head onboarding manifest requires and finds every actual provider/name; no TODO; disabled target passes record gate; BANNED cannot be admitted.
6. **Add Needs you artifact/render route.** Consume Add pending evidence through guarded owner path; no automatic enabling. Acceptance: exactly one stable item for no-safe names, reason visible, owner answer durable, rerun quiet.
7. **Preserve monogram.** Add no logo files or LOGOS entries; test fallback/provenance boundary. Acceptance: new enabled target card uses first-letter tile and no remote asset; disabled target is not in catalog.
8. **Add W17a contract tests.** Include fake GitHub/index/bundle/list/issue fixtures, schema/property tests, hostile input fixtures, atomic-write failure, and no-safe disabled path. Run the focused 112 baseline plus new tests; then the full Validate contract set.

### W17b: Pages link, PR, named smokes, and owner handoff

1. **Pages link.** Add static GitHub workflow link and documentation of owner/write refusal. Acceptance: link works; portal has no token, Authorization, dispatch endpoint, or secret input.
2. **Dispatch Add path.** Wire new fields to the plan/finder while preserving legacy actions. Acceptance: only write-authorized user can execute on GitHub; non-owner behavior is documented, not simulated; input is env/argv-safe.
3. **Open PR and dispatch checks.** Preserve workflow-file guard; create/reuse branch/PR; dispatch Validate and Onboarding review against exact head. Acceptance: PR body contains complete evidence and branch-refused fallback is clear.
4. **Dispatch two exact provider-named smokes.** Dispatch primary and first fallback with `provider`, `publish=false`, `keep_going=false`; no new secret. Acceptance: both runs exist for exact head, provider winner matches requested provider, failures/blocking dispatches are red/waiting, and no release occurs.
5. **Third-provider promotion boundary.** Do not write/smoke third in the initial target. Acceptance: third appears only as deferred evidence; a later owner run must wire it and pass its own named smoke before it can become a fallback.
6. **Owner merge/publish handoff.** Do not auto-merge or auto-publish. Acceptance: run summary/PR says owner merges only after Validate + Onboarding + both named smokes; owner separately publishes/phone-tests. After merge, `pagegen`, `readmegen`, `credits`, `obtainium`, and portal contracts show the enabled app.
7. **Rehearse fake GitHub end to end.** Required acceptance matrix: happy path; named primary loses to fallback => STOP; paid/held name => Needs you and disabled target; broken provider bundle (CCleaner-style) => disabled with precise reason; rerun twice => no duplicate target/PR/smokes/Needs item; third deferred; failed issue API => `unable to check`, never `none`.

## What was not verifiable in this read-only, no-network review

- I could not exercise GitHub’s real permission refusal, workflow dispatch, Actions run identity, provider Issues API, release asset downloads, APKMirror/APKPure pages, live `list-patches`, or a phone install. The proposed fake-GitHub tests must cover these branches; real first use still needs owner observation.
- I did not verify the current remote default branch contents beyond this checkout or any future provider bundle/version. Claims above about current code are anchored to commit `b5a13c48b96a8a72ab6ad3112e5af4dab49bc4f7`.
- The repository has no existing Add-specific provider finder, provider-issue searcher, plan schema, Add-to-Needs-you artifact route, or provider-named smoke dispatch; those are identified gaps, not inferred implementations.
- I did not alter `a read-only clone` or any external workspace content.
