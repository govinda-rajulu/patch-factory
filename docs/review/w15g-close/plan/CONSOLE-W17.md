# Console / Add-app review design

**Status:** design recommendation only; no repository or GitHub writes were made by this research.
**Date basis:** repository checkout reviewed at the 31 October 2026 checkpoint, plus the public GitHub documentation linked below.

## Recommendation in one paragraph

Use the public Pages site only as a **read client and URL builder**. It must never call a GitHub write endpoint, hold a token, or claim that a checkbox is an authorization. Add two GitHub issue forms: a short **Add-app request** form and a short **owner decision** form. The first `issues:opened` workflow validates the untrusted form, discovers providers, obtains live patch/version evidence, and runs a bounded, secretless nonpublishing test. It publishes the result as an issue comment/body and (for a non-owner request) a **draft, non-mergeable evidence PR**. The owner opens the static console against that issue, ticks/unticks patches and writes an optional note; the console makes a second issue-form URL. The owner presses **Submit** on GitHub. A second workflow accepts that decision only when the issue author and actor are the repository owner, re-fetches and verifies the original plan digest, then invokes the existing add/validation/onboarding machinery through a PR. That PR writes `DECISIONS.json` plus a dated decision note and selected patch configuration; it is still merged and published only by the owner. Any non-owner request may test, but can only remain a draft/branch and can never add release data.

This is safer than putting a form in Pages because the current portal contract explicitly says read-only and tests for the absence of credentials and write endpoints ([`docs/portal.js:1-2`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/portal.js#L1-L2), [`tests/portal_contracts.cjs:40`](https://github.com/govinda-rajulu/patch-factory/blob/main/tests/portal_contracts.cjs#L40)). It also preserves the repository's explicit house rule that `5. Add target` opens a PR but does not merge, build, or publish ([`add-target.yml:1-7`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L1-L7)).

## What the current repository proves

* **Pages is read-only today.** `portal.js` reads allow-listed API/raw URLs, uses `credentials: 'omit'`, and refuses 403/429 rather than obtaining a token ([`docs/portal.js:46-67`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/portal.js#L46-L67)). It also renders user/data strings with `textContent` rather than `innerHTML` ([`docs/portal.js:35-38`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/portal.js#L35-L38)). Preserve those boundaries.
* **Existing Add is a legacy owner-operated dispatch.** It takes `workflow_dispatch` inputs including `id`, package, provider and patch names ([`add-target.yml:11-71`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L11-L71)), passes them through environment variables to `app.py`, and opens a branch/PR ([`add-target.yml:90-139`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L90-L139)). It does not discover candidates, present a patch checklist, or publish automatically.
* **The existing Explore path is the live-probe precedent.** It validates provider/package shapes, downloads a verified patcher, fetches a bundle with channel fallback, and invokes `list-patches` ([`explore.yml:41-110`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/explore.yml#L41-L110)). Extract the safe transport into a reusable finder rather than copying shell snippets into the console workflow.
* **Onboarding is deliberately data-only and nonpublishing.** The checker reads the base commit and only selected head data paths, then the agent review has no merge/publish job ([`onboard-review.yml:5-12`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/onboard-review.yml#L5-L12), [`onboard-review.yml:68-115`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/onboard-review.yml#L68-L115)). Reuse that property for generated console PRs.
* **Owner decision grammar already exists.** The Needs-you renderer embeds item metadata and instructs `take G2`, `take N-xxxxxx`, `take all`, `yes all`, `drop`, and `hold` ([`needs_you.py:1040-1115`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L1040-L1115)); its parser ignores prose/unknown ids, supports groups, and gives later commands precedence ([`needs_you.py:705-736`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L705-L736)). The owner-only comment guard checks title, exact owner login, `author_association == OWNER`, and non-bot user ([`needs_you.py:752-758`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L752-L758)). Use the same IDs/semantics; do not invent a second meaning for “take/drop/hold”.
* **Decisions are durable and normalized.** `DECISIONS.json` says calls are matched per target/name after normalization and that `drop` is never asked again; its current entries contain target, name, call, N-id and date ([`src/patches/DECISIONS.json:1-16`](https://github.com/govinda-rajulu/patch-factory/blob/main/src/patches/DECISIONS.json#L1-L16)). A console decision must append equivalent rows, not merely leave a checkbox state in an issue.
* **Existing watch workflows have one-writer/concurrency lessons.** Community and selection watch serialize their main writers with `main-writer` ([`community-watch.yml:9-18`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/community-watch.yml#L9-L18), [`selection-watch.yml:12-24`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/selection-watch.yml#L12-L24)). The new flow needs a separate `console-request` concurrency key and a main-moved/deduplication stop, not another racing writer.
* **W17a/W17b and the ready-PR item are not shipped.** The brief says current Add does not discover providers, list live patch names, classify names, search provider issues, create a new-app Needs-you item, or dispatch provider-named smokes ([`W17-BRIEF.md`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/W17-BRIEF.md)). The map splits discovery/policy/staging (W17a) from Pages link, dispatch, named smokes and rehearsal (W17b) ([`W17A-MAP.md`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/W17A-MAP.md)). `OPEN-WORK` separately records “discovery, scan smoke, green test build, ready PR” as not orchestrated ([`OPEN-WORK.md:36-42`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/OPEN-WORK.md#L36-L42)). This design absorbs all three rather than introducing a third orchestrator.

## GitHub issue-form and URL-prefill facts

GitHub’s [issue-form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema) requires unique `id` values and states that an `id` is the canonical identifier for URL-query prefills. Its `input` and `textarea` elements are text fields; the form response is converted to Markdown in the created issue ([issue-form syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-contributions-to-your-repository/syntax-for-issue-forms)). GitHub’s [creating-an-issue documentation](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue#creating-an-issue-from-a-url-query) confirms that URL query parameters can fill custom text fields in issue-form templates and that `template` can select a template.

The same documentation warns that a URL over the server limit returns **414 URI Too Long**; it does not promise one universal byte limit. Therefore:

1. Use short field IDs and compact values (`request`, `plan`, `take`, `note`), URL-encode with `URLSearchParams`, and enforce a conservative local URL budget (for example 6,000 characters) rather than relying on an undocumented maximum.
2. Put only stable short N-ids in `take`/`drop`; do not put APK bytes, full patch descriptions, or arbitrary Markdown in a URL. Store the authoritative plan in the workflow artifact/issue comment and verify its SHA-256 later.
3. If the generated URL exceeds the budget, show a clear fallback: open the empty issue form and paste the compact IDs. Never silently truncate selections or notes.
4. Treat every prefilled value as editable and untrusted. The issue workflow must re-validate fields and re-fetch the trusted plan. A prefilled URL is convenience, not authentication.
5. Add a browser/manual contract test that opens each form URL and confirms `input`/`textarea` values are prefilled by their **field IDs**. Do not depend on prefill for dropdowns or checkboxes; the docs specifically guarantee custom text-field prefills, while the dynamic patch list cannot be a static checkbox list in a YAML form.

## Proposed end-to-end data flow

### A. Discover request (one owner click from Pages, then Submit on GitHub)

1. Pages adds a plain external link, not a fetch or dispatch call: `https://github.com/govinda-rajulu/patch-factory/issues/new?template=console-request.yml&request=<encoded-query>`. The link may be visible to everybody.
2. `.github/ISSUE_TEMPLATE/console-request.yml` has only bounded text fields: `request` (required; label or package), optional `store_url`, optional `note`, and a displayed warning that only the owner can make anything live. The portal should prefill `request` and `store_url`; omit a large patch list at this stage.
3. On `issues:opened`, `console-request.yml` runs from the default branch. It parses the issue body as hostile Markdown/data, not as shell/YAML/JSON instructions. It accepts only expected headings/fields, strips control characters, applies byte/line limits, and rejects duplicate or missing values.
4. `src/etc/provider_finder.py` resolves package/label, ranks official Morphe first, then exact community-index candidates, probes live bundles and `list-patches`, checks a fitting ARM64/API-29 store APK using the existing variant picker, and records exact release/tag/asset/hash evidence. Failed fetch/API/probe is `UNKNOWN` with a reason, never “none”. This follows the W17 brief’s provider-finder rule and existing `explore` transport; the index alone is not proof.
5. The workflow writes a bounded `console-plan.json` as an artifact and a sanitized issue report. The plan contains request key, package/id/label, providers and roles (`primary`, first `fallback`, `deferred`), patch names/descriptions, safe/held/BANNED classification, provider-issue evidence, store/version evidence, selected defaults, a plan digest, and expiry/created timestamp. Keep the full plan out of the URL.
6. The workflow runs at most the configured smoke budget (one primary and one fallback per app; no third provider smoke until promoted). It is nonpublishing. W15g should precede this path where possible: its design puts the patch job behind `contents: read`, no secrets, and `--unsigned`, then isolates signing and publishing ([`SIGNING-SPLIT.md:1-30`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/SIGNING-SPLIT.md#L1-L30)). Until W15g is live, **do not** route an untrusted request through a job that sees a keystore, signing password, publishing token, or provider-controlled code.
7. The workflow updates the request issue with a compact result and a link such as `https://govinda-rajulu.github.io/patch-factory/?console_issue=<number>`. The portal reads the public plan/report (prefer a committed report or a read-only API endpoint that is already allow-listed; do not teach the browser to read arbitrary issue URLs without a strict allow-list).

### B. Owner patch selection and note (two clicks for the final action)

1. The console validates the issue number, displays only the trusted plan rows, and defaults to the plan’s safe names. BANNED names are never selectable. Held names show their reason and N-id; they are not silently enabled.
2. The owner ticks/unticks patch rows and enters an optional note. The UI constructs a compact owner-decision URL for `console-decision.yml`, containing issue number, plan digest, selected N-ids, and note. The URL must be encoded and length-checked as above.
3. The owner clicks **Review decision on GitHub** (first click), verifies the form, and clicks **Submit new issue** (second click). The form itself must say that only the repository owner’s submission can create a ready PR. A non-owner can submit a decision-shaped issue, but it is recorded/tested only and cannot affect the release tree.

### C. Owner decision and PR

1. `console-decision.yml` runs on `issues:opened` but immediately checks all of: issue form type/marker, `github.actor == github.repository_owner`, issue author login equals repository owner, `author_association == OWNER`, non-bot account, and a valid request/plan issue link. Never rely on a checkbox such as “I am the owner”.
2. It re-fetches the original request issue and the immutable trusted plan artifact/commit, compares the supplied digest, confirms the plan is not expired, and confirms the request is not already consumed. It validates selected IDs against the plan; unknown, duplicate, conflicting, or omitted IDs stop with no write.
3. It recomputes target identity, provider evidence and classification from the trusted plan. It must not trust provider names, patch names, store URLs, or “green” text copied into the form body. The plan digest binds the exact result the owner saw.
4. It creates a branch and **draft PR** from current `main`, then invokes the plan-aware Add path. The branch includes target/provider/patch data, `src/patches/DECISIONS.json` entries, and `docs/review/decision-notes/YYYY-MM-DD-console-<request-key>.md`. It should not directly write `main`, release tags, Pages output, or a secret.
5. It runs `3. Validate`, Onboarding review, primary/fallback provider-named smoke builds, and (if enabled after W15g) the secretless scan smoke. All checks must be green before the PR is marked ready. “Ready” does **not** mean merged. The owner reviews, merges, and publishes.
6. The workflow comments a receipt with PR URL, plan digest, selected/dropped/held counts, smoke links, and exact stop reasons. A rerun with the same request key and plan digest is a no-op or resumes the existing PR; it never duplicates target folders, N-rows, branches, or releases.

### D. Non-owner request path

A non-owner `console-request` may run discovery and a tightly capped secretless smoke, but its result is permanently nonpublishing:

* label the issue/PR `console-nonowner`, keep the PR draft, and do not let `rule-merge` select it;
* never write `DECISIONS.json`, `src/targets.json`, release metadata, `docs/` generated catalog, or Pages output from the non-owner path;
* if a branch is needed for reproducible evidence, write only `docs/review/console-evidence/<request-key>/` or a workflow artifact, not an enabled target;
* no secrets, signing material, `contents:write` credentials in the test job, provider-repo writes, or arbitrary code checkout; use the base commit and fixed argv;
* only the owner decision workflow may promote the same plan to a ready PR.

If GitHub permission or policy makes a draft PR unsafe to create from an issue-triggered run, the safe fallback is an issue comment plus artifact and no branch. Never weaken the owner gate merely to satisfy the draft-PR convenience.

## Files and workflows

### Phase 0 — safety prerequisite and shared library

**Change/add:**

* `.github/workflows/console-request.yml` — `issues:opened` entry point, strict concurrency and budgets, discovery/report path; no signing secrets.
* `.github/workflows/console-decision.yml` — owner-only decision gate and PR orchestrator; its first step is identity/digest verification.
* `.github/ISSUE_TEMPLATE/console-request.yml` and `console-decision.yml` — short text fields with unique IDs and explicit owner/non-owner warning.
* `src/etc/console_form.py` — parser for form-generated Markdown, bounded field extraction, normalization, request-key/digest validation, and URL-sized decision encoding. It must treat body as untrusted and reject ambiguous shapes.
* `src/etc/provider_finder.py` — deterministic provider discovery/evidence plan; reuse `community_model`, `onboard_scout` only as candidate leads, `provider_watch`/`explore` transport, `variant_pick`, and existing issue API conventions.
* `src/etc/decision_note.py` — sanitize and render a dated note; this is a record writer only, not an auto-lesson writer.
* `tests/console_form_contracts.py`, `tests/provider_finder_contracts.py`, `tests/decision_note_contracts.py`, plus workflow YAML/no-interpolation contracts.

**W15g dependency:** make W15g the gate before any real APK test from a public issue. Its stated goal is that third-party patch code never runs beside the release key/write token. The planned patch job is keyless/secretless and `--unsigned`; the sign job alone sees the release key; publish sees no key ([`SIGNING-SPLIT.md:3-15`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/SIGNING-SPLIT.md#L3-L15)). A fixture-only discovery rehearsal can be developed before W15g, but production console smoke should stop with `W15G_REQUIRED` until its full nonpublishing batch and phone test pass.

### Phase 1 — smallest safe first: request -> discovery -> owner-visible report

* Add the issue form and external Pages link. The Pages link test belongs in `tests/portal_contracts.cjs`; retain the current test that rejects `localStorage`, `Authorization`, `/dispatches`, and `method:` ([`tests/portal_contracts.cjs:40`](https://github.com/govinda-rajulu/patch-factory/blob/main/tests/portal_contracts.cjs#L40)).
* Add discovery and report only. No target writes, no DECISIONS write, no release output.
* Reuse `explore.yml`’s provider/package validation and `list-patches`; reuse `selection_watch` classification and `decisions.py` normalization rather than duplicating ADOPT/BANNED/CONFIRM policy.
* Add fake-GitHub tests for owner, non-owner, malformed body, hostile Markdown, provider failure, 429/403 issue lookup, empty list, unsupported version, no fitting APK, and rerun.

Acceptance: owner can open one URL, submit one request, see an issue report with provider evidence and safe/held rows, and no repository release data changes.

### Phase 2 — owner checklist -> decision PR

* Add the console plan reader and compact decision URL builder.
* Extend the form parser to accept only `request_issue`, `plan_sha256`, `take_ids`, and `note` with strict limits. The selection UI may send all chosen IDs; unchecked rows become explicit `drop` decisions in the trusted plan, not an implicit omission.
* Add `app.py` plan-aware mode or a reusable `workflow_call` entry used by both legacy `add-target.yml` and `console-decision.yml`. Do not fork target-writing semantics.
* Reuse `add-target`’s branch/PR/check dispatch shape ([`add-target.yml:106-139`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L106-L139)), but add a plan digest and request key before the first write. Preserve legacy inputs and explicitly remove/disable the public `approve_confirm` shortcut for console requests ([`add-target.yml:63-71`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L63-L71)).
* Write `DECISIONS.json` one row per patch (`target`, normalized name, `take`/`drop`/`hold`, N-id, UTC date), preserving existing hard holds: BANNED remains omitted; paid/CONFIRM/reserved/duplicate names remain held unless the existing policy explicitly allows the owner decision.
* Write a dated decision note under `docs/review/decision-notes/`. Suggested shape:

  ```markdown
  # Console decision · 2026-10-31 · request <short-key>
  Request: #<issue>  
  Plan SHA-256: `<64 lowercase hex>`  
  Submitted by: @<owner>  
  Submitted at: <UTC ISO-8601>

  ## Result
  - target/package: `<validated values>`
  - provider roles: primary `<OWNER/REPO>`, fallback `<OWNER/REPO>`
  - selected: `<N-id>` …
  - dropped: `<N-id>` …
  - held/deferred: `<N-id>` …

  ## Owner note
  <bounded plain text, rendered as text; no executable Markdown/HTML>

  ## Lesson candidate
  <copy the note or a short sanitized observation here only; this is not yet a lesson>
  ```

  The note is evidence/history, not a command source. Do not automatically append `docs/council/LESSONS.md`: that ledger is explicitly append-only and says new entries require owner-approved proposals and exactly one Tags line ([`docs/council/LESSONS.md:1-7`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/council/LESSONS.md#L1-L7)). `knowledge/LESSONS.md` describes the council ledger as canonical and keeps cross-session lessons that are not in it ([`knowledge/LESSONS.md:1-7`](https://github.com/govinda-rajulu/patch-factory/blob/main/knowledge/LESSONS.md#L1-L7)). A later owner-approved lesson PR can copy a “Lesson candidate” into the canonical format.

Acceptance: only the owner’s valid decision makes a ready PR; the PR contains durable decisions and history; a second identical submission is a no-op; no merge or release occurs automatically.

### Phase 3 — green gate and ready PR

* Dispatch exact provider-named smokes from the Add/console orchestrator, because bot-created PRs do not automatically start all required workflows in this repository. Existing Add explicitly dispatches Validate and Onboarding after PR creation ([`add-target.yml:131-135`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/add-target.yml#L131-L135)).
* Reuse `onboard-review.yml` unchanged where possible. Add console PR metadata only if the checker needs to distinguish disabled/pending targets; keep the head-data-only safety model.
* Add a `console-owner-gated` label and make `rule_merge.py` refuse automatic merge for console PRs. The owner remains the only merger/publisher, in line with the brief’s owner answer. `rule-merge` currently describes an automatic green merge for selection-watch PRs ([`rule-merge.yml:1-5`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/rule-merge.yml#L1-L5)); do not let that general mechanism accidentally merge an Add-app PR.
* Use a state machine: `REQUESTED -> PLAN_READY -> DECIDED -> TESTING -> READY_FOR_OWNER -> MERGED/PUBLISHED`, with `FAILED`, `HELD`, `DISABLED`, and `NONOWNER_DRAFT` terminal/intermediate states. “Green test” is not “merged”; current lessons explicitly separate configured/applied/approved/published ([`docs/council/LESSONS.md:33-36`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/council/LESSONS.md#L33-L36)).

Acceptance: a qualifying owner decision produces a draft PR, named smokes and validation; all green may mark it ready, but only the owner’s normal GitHub merge and release action changes live output.

### Phase 4 — optional portal polish and lessons intake

* Add issue/plan status cards to Pages using only allow-listed public reads and safe `textContent` rendering. Avoid an issue-writing API forever.
* Add an owner-facing “copy lesson candidate” link, not automatic lesson mutation. A future owner-approved PR can add a `### L###` entry with a `Tags:` line; never turn an arbitrary note into council instructions.
* Add retention cleanup for artifacts only after an owner-approved policy; retain plan digest, decision note and PR links long enough to audit the release.

## Exact gatekeeping rules

1. **Identity:** owner means the exact repository-owner login and non-bot account, plus `author_association == OWNER`; `github.actor` must also equal the owner on the decision event. Organization ownership or a display name is not enough.
2. **Event separation:** discovery can be public; promotion is a different event/workflow. Never give a public issue body a direct path to `contents:write` plus release/signing secrets.
3. **Trusted base:** run controller code from the default branch/base commit. Never check out an attacker’s issue branch or execute provider-supplied scripts. Provider bytes are data; use fixed argv, timeouts, byte caps, and hashes.
4. **Plan binding:** the decision contains a request issue number and SHA-256 plan digest. The workflow downloads/recomputes the plan and stops on mismatch, expiry, duplicate consumption, unknown IDs, duplicate IDs, or conflicting selection.
5. **Patch policy:** safe described names may default on; BANNED never enters an include list; CONFIRM/paid/reserved/no-description/generic/no-switch/risky/duplicate names are held with reason. Existing `DECISIONS.json` is memory, not a bypass; `drop` stays dropped. “No safe names” creates a disabled/pending record, not a release.
6. **Provider policy:** providers are auto-added from live-qualified primary/first fallback evidence. The owner reviews patches, not arbitrary provider URLs. A provider failure is unknown/held; never call it “no issues” when the API was unavailable. A third provider is deferred until separately wired and smoked.
7. **Smoke policy:** at most two provider-named smokes per app in the first path. A fallback only qualifies when its own named smoke passes. Scan smoke is advisory and nonpublishing; a green name/list check is not proof of a green patch build.
8. **Write policy:** owner decision PR is the only path that may write target/release data or `DECISIONS.json`. No workflow auto-merges or publishes it. A non-owner branch stays draft and must be excluded from `rule-merge`.
9. **Input policy:** all issue form fields and comments are untrusted. Reject controls, overlong values, invalid package/provider/URL shapes, duplicate form headings, shell metacharacter interpolation, unsafe Markdown links, and malformed N-ids. Pass values in environment variables or fixed argument arrays, as existing Add does.
10. **Idempotence:** request key = normalized package/target identity + plan digest (and provider identities). Search open/closed console issues, branches and PRs before writing. A retry resumes or reports the existing receipt; it never emits duplicate target folders, decisions or releases.
11. **Cost/rate limits:** one active run per request key, one request per package window for non-owners, max provider candidates 3, max two smokes/app, max APK/bundle bytes and wall-clock time, no parallel public request storm, cancel duplicate runs, and stop on GitHub 403/429. Do not let user-selected URLs determine arbitrary hosts or artifact sizes.
12. **Release visibility:** Pages and Obtainium only update after owner merge plus the repository’s normal release/publish path. “Built”/“ready” is shown separately from “published”.

## Reuse map

| Existing component | Reuse | Required change/guard |
|---|---|---|
| `src/etc/needs_you.py` parser and item IDs | Preserve `N-xxxxxx`, `take/drop/hold`, groups, normalization-compatible semantics; use its complete-line parser for an optional compatibility comment path | Extend catalog metadata for console plan IDs only if tests prove no ambiguity; do not parse arbitrary issue prose as a command |
| `src/etc/decisions.py`, `src/patches/DECISIONS.json` | Existing name normalization and durable owner memory | Append rows only in owner decision PR; retain hard policy precedence and stable dates/IDs |
| `add-target.yml` / `src/etc/app.py` | Target schema, patch folders, options, provider records, PR/check dispatch | Add a plan-aware/reusable mode; verify digest before any write; remove console use of `approve_confirm` |
| `explore.yml`, `provider_watch.py` | Verified patcher, channel fallback, list-patches parsing, bounded transport | Refactor to library calls; strict no-secret provider execution and issue API failure states |
| `selection_watch.py`, `ADOPT.json`, `BANNED`, `CONFIRM` | Existing classification and safe defaults | Make new-target “all held/no safe names” a disabled target outcome and produce one stable Needs-you item |
| `onboard-review.yml` / `onboard_check.py` | Base/head data-only checker and review manifest | Add disabled/pending schema cases and console PR label rules; no attacker head checkout |
| `rule-merge.py` | Existing check aggregation and green-gate vocabulary | Explicitly exclude `console-owner-gated`/new-app PRs from automatic merge |
| `needs-you.yml` | Existing owner issue and comment guard; issue may link to the console plan | Do not let a new workflow create a second “Needs you”; use the existing issue or a plan-specific issue comment |
| `docs/portal.js` / `portal_contracts.cjs` | Safe external-link and read-only contract | Add only URL builder/allow-listed read status; keep no token, no write endpoint, no arbitrary HTML |
| `docs/council/LESSONS.md`, `knowledge/LESSONS.md` | Note/lesson governance and formats | Save a dated decision note first; lessons require a separate owner-approved PR |

## Tests and rehearsal matrix

### Unit/contract tests

* Form schema: required top-level keys, unique IDs, only expected input/textarea fields, bounded validation values, warning text.
* URL builder: correct `template` and field-ID query names; UTF-8/ampersand/quote/newline encoding; no token/Authorization/write endpoint; under conservative budget; explicit over-budget fallback.
* Body parser: normal form output, reordered fields, missing/duplicate labels, forged headings, HTML/Markdown injection, controls, oversized note, invalid N-id/package/provider/URL, and fields edited after prefill.
* Identity: owner, owner-associated owner, non-owner, bot, fork-like metadata, actor/issue-author mismatch; no write on every failure.
* Plan binding: digest match/mismatch, expired/missing/altered artifact, unknown/duplicate IDs, rerun/no-op, package collision, provider evidence changed.
* Policy: BANNED always omitted; CONFIRM/paid/reserved/no-description/generic/no-switch/risky/duplicate held; `take`/`drop` memory applied according to existing rules; all-held creates disabled target and one stable N-item.
* Provider: official-first ranking, exact package index candidates, duplicate repository merging, empty/malformed list, timeout/403/429, provider issue “none/matches/unable”, version/API ceiling, no fitting APK, third provider deferred.
* Writes: staged atomic transaction, no files on anchor/digest failure, no partial target, valid JSON and onboarding record, decision note escaped/bounded.

### Workflow/rehearsal

Use a fake GitHub that enforces documented CLI/API fields and real event shapes. Run the shipped controller, not a simplified copy (the lessons explicitly require an exact-controller rehearsal: [`docs/council/LESSONS.md:186-189`](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/council/LESSONS.md#L186-L189)). Cover:

1. owner happy path: request -> plan -> selected patches -> green named primary/fallback -> ready PR;
2. owner selects a held/paid name: remains held unless the existing policy/decision semantics allow it;
3. provider loses to fallback: stop/hold primary and require the fallback’s own named smoke;
4. broken bundle/empty list/unknown store variant: disabled or held with precise reason;
5. non-owner: discovery and capped secretless smoke only, draft PR/branch, never ready/release/DECISIONS write;
6. forged owner checkbox, forged issue author, actor mismatch, malformed body, hostile note;
7. stale plan digest, changed main, duplicate request, rerun twice, issue/API 403/429;
8. all required checks green but PR remains owner-gated; owner merge is the only publish transition.

## Alternatives judged

### 1. Issue-form URL (recommended)

**Pros:** works with public static Pages; no browser token; GitHub identity and repository permissions are applied at submission; structured fields and issue history are visible; forms can be prefilled by field ID; an `issues:opened` workflow can perform discovery and re-check identity. It gives the owner the requested final GitHub Submit click.

**Cons:** form body is Markdown and editable; URL size is bounded by an undocumented server limit; dynamic checkboxes cannot be generated in YAML; issue events can be spammed. Mitigate with strict parsing, short IDs, plan digest, rate/cost caps, and owner-only promotion.

### 2. Issue comments on #233 (fallback/compatibility path)

**Pros:** the repository already has the exact owner guard and `take/drop/hold N-xxxxxx`, group commands, dedupe ledger, and `needs-you.yml` ([`needs-you.yml:69-109`](https://github.com/govinda-rajulu/patch-factory/blob/main/.github/workflows/needs-you.yml#L69-L109)). It is familiar to the owner.

**Cons:** comments cannot safely carry a large dynamic selection UI; free text is easier to misparse; a public portal cannot write the comment; the comment event gives less clear request/plan binding than a dedicated form. Keep comments for small decisions and compatibility, not as the main Add console.

### 3. `workflow_dispatch` link

**Pros:** existing `add-target.yml` already has a form and permission boundary; an owner with write access is the only person who can execute it.

**Cons:** it cannot be submitted by a non-owner for test-only staging; it does not naturally preserve an issue-form history/note; its current fields ask for low-level id/package/provider/patch syntax and include an `approve_confirm` checkbox; GitHub Actions dispatch is not a dynamic patch checklist. It is suitable as the legacy/manual fallback, not the new console.

### 4. GitHub Discussions

**Pros:** better long-form conversation and public history; can collect feedback before issue conversion.

**Cons:** discussion form answers and events are a weaker fit for an owner-only transactional gate; conversion/author metadata and workflow handling add another state machine; no advantage over an issue form for compact IDs and a plan digest. Use only for community suggestions, never as the release authorization surface.

### 5. Browser token/API or server-side proxy

Reject. A token in Pages is exposed to every visitor, and a proxy becomes a new privileged service/secrets boundary. It violates the stated constraint and the current portal contract.

## Owner steps (target: two clicks for each final decision)

### Add request

1. In Pages click **Add an app**; it opens the prefilled GitHub request form.
2. Check the short request/store values and click **Submit new issue**. Wait for the workflow’s plan/result link.

### Patch decision after results

1. In Pages open the request result; tick/untick patch rows, optionally type a note, click **Review decision on GitHub**.
2. Verify the prefilled plan digest and click **Submit new issue**. The owner later reviews/merges the ready PR as the normal release decision; that final merge is deliberately not automated.

If “two clicks” is interpreted as including merge, that is unsafe and conflicts with the owner’s current “owner merges/publishes” answer. The safe interpretation is two clicks to submit each request/decision, followed by the explicit owner merge/publish step.

## Android Auto (feature request only; not part of this delivery)

The repo has no `com.google.android.projection.gearhead` target in its current `src/targets.json`/community index search, so do not imply that Android Auto is ready to add. A future Android Auto packet would need:

* a target record for the exact package and a verified source/store variant, including version/API/architecture/signing and likely system/privileged-app constraints;
* provider live evidence for the exact package, not merely a patch whose description mentions Android Auto;
* Android Auto-specific device/vehicle smoke criteria (phone-side connection, head-unit display, media/navigation behavior, Google Play services or MicroG compatibility, and rollback);
* explicit risk review for certificate/signature bypasses and privileged permissions; Android Auto may reject re-signed apps or require platform-side privileges, so an APK patch alone may not be sufficient;
* target/provider records and normal onboarding/release gates only after a real fitting APK and phone/head-unit test.

Public GitHub evidence shows that **Morphe’s main patches repository** has an “Android Auto” patch described as bypassing certificate checks and restoring YouTube Music playlists/podcasts in Android Auto ([`MorpheApp/morphe-patches`](https://github.com/MorpheApp/morphe-patches/)); that is evidence for related YouTube Music functionality, not proof that `com.google.android.projection.gearhead` itself is a supported target. A package-specific search also finds Android Auto system/permission work referencing `com.google.android.projection.gearhead` in [AICP/frameworks_base](https://github.com/AICP/frameworks_base/commit/80e52ff91e43ebaa9f24f94a16894a95549ea1c1), and a separate open-source phone-side replacement in [mretallack/AndroidAuto](https://github.com/mretallack/AndroidAuto). These are leads only; they are not approved patch providers for this repo. The future finder should search Morphe/ReVanced/community bundles for the exact package, verify a live bundle and source APK, and then require the same owner-only plan/smoke/merge gates.

## Material limitations and unresolved points

* GitHub documents that URL-prefill supports custom text fields and that overlong URLs return 414, but does not publish a universal byte limit in the cited page. The conservative local cap and browser contract test are therefore required.
* An issue-form response is rendered Markdown and can be edited after the URL is built. The workflow cannot trust labels, checkbox text, or issue title; only a revalidated plan digest and strict parser can bind it.
* A public `issues:opened` trigger can be abused for compute and issue/PR volume. GitHub-native rate controls, concurrency, actor/package windows, hard timeouts, artifact caps, and a no-branch fallback are required. Exact quotas depend on repository/GitHub plan and should be measured before enabling public smokes.
* The current brief/map leaves the exact disabled-target cross-consumer schema and the final W15g implementation open. Do not call Phase 2 production-ready until disabled targets pass the full suite and W15g’s nonpublishing batch plus phone test pass.
* Provider issue lookup is evidence only, not an admission decision. Public API failures must remain `unable to check`, not `none`.
* No web search was treated as proof of Android Auto support. The package-specific provider/release/version/signing evidence and a real phone/head-unit test remain unverified until a future feature packet.
