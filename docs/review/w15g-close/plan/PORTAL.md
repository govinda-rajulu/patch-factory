# Portal and status-page design memo

**Scope and date:** read-only review of `patch-factory` at the supplied clone and the supplied
`status.json` snapshot (owner asks, 31 Oct 2026). No repository files were edited. The snapshot
contains 17 enabled apps; CCleaner is not in `apps` because status generation intentionally filters
to enabled targets.

## 1. One freshness row per built card

### Current behavior / source

`docs/portal.js` currently renders two independent facts in `appsPanel()`:

- `patchAgeField()` emits `Patch age: ` followed by `age+' days / '+limit+'-day limit'` and a warning only after the limit (`docs/portal.js:521-533`). This produces the grammatical bug `1 days` and makes `180-day limit` look like normal status on every card.
- The next call is `field(article, 'Last built', ...)` (`docs/portal.js:597-601`), using the release-record `built` timestamp first and the release metadata fallback. `stamp()` adds the human date/time and relative age (`docs/portal.js:41`).

The supplied snapshot confirms patch age and last-build are separate data: for example, Amazon Music
has `patch_age_days: 1`, `max_patch_age_days: 180`, and `last_build.when: 2026-10-30T20:45:22Z`.
The age is advisory in the producer too: `src/etc/status.py:419-427` computes an over-limit
`patch_age_warning` but does not gate a build. Keep that policy.

### Proposed design (exact changes)

**Primary wording:** `Freshness: patch bundle updated 1 day ago · last built Oct 30, 12:06 AM (32 h ago)`.

Two acceptable alternatives for owner review:

1. `Build freshness: patch bundle 1 day old · built Oct 30, 12:06 AM (32 h ago)`
2. `Release freshness: patch bundle updated 1 day ago · last built Oct 30, 12:06 AM (32 h ago)`

Use “Freshness” as the short field name. It makes clear that these are two clocks without exposing the
implementation names `patch_age_days` or `last_build`.

Change **`docs/portal.js`**, replacing `patchAgeField()` and the separate `field(...,'Last built',...)`
call with one pure/display helper, for example:

```js
function daysWord(n){return n===1?'day':'days';}
function freshnessField(article,target,statusRow,top,built){
  const limit = ...; // same status-row, target, then 180 fallback
  const age = ...;   // same status-row/release fallback
  const builtText = built || 'time unknown';
  const p=el('p',undefined,'card-field freshness-field');
  p.append(el('strong','Freshness: '));
  if(age===null) p.append(document.createTextNode('patch age unavailable · last built '+builtText));
  else p.append(document.createTextNode('patch bundle updated '+age+' '+daysWord(age)+' ago · last built '+builtText));
  // Show the cap only for a near/exceeded warning, never for ordinary cards.
  const near = age!==null && age >= Math.max(1, limit-14);
  const exceeded = age!==null && age > limit;
  if(near || exceeded){
    const message = exceeded
      ? ' — WARNING: patch bundle is over the '+limit+'-day advisory limit.'
      : ' — WARNING: patch bundle is within 14 days of the '+limit+'-day advisory limit.';
    p.append(document.createTextNode(message)); p.className += ' warning';
  }
  article.append(p);
}
```

The exact implementation should preserve an existing non-empty `statusRow.patch_age_warning` (it is
server evidence), but avoid printing the cap unless `near || exceeded`. At the boundary, `age === limit`
is “near”; `age > limit` is “exceeded”. Keep “advisory; build gates still decide” in the warning,
not in every ordinary card. If the owner prefers percentage rather than a fixed window, use a documented
90%-of-limit rule; do not leave “near” implicit.

Call it with the currently duplicated built-value expression, calculated once:

```js
const built=record&&... ? stamp(record.built) : buildMeta(top).replace('Last built ','');
freshnessField(article,t,statusRow,top,built);
```

Do **not** change `src/etc/status.py` merely to fix display. Its existing over-limit warning and the
`tests/status_contracts.py::test_patch_age_is_utc_advisory_data_only` contract are useful producer
coverage. Add a backend field only if “near” must be consumed by another client; otherwise this is a
portal presentation rule.

### Test impact

- Extend `tests/portal_contracts.cjs` with a pure exported `freshnessText(age,limit,built)` (or
  equivalent) contract: `1` says `1 day`, `0` says `0 days`, ordinary `1/180` omits `180-day`,
  `166/180` includes a near warning, `181/180` includes an exceeded warning, and invalid age still
  shows the built timestamp. Assert the source no longer contains the old `age+' days / '+limit` form.
- Keep `tests/status_contracts.py` unchanged except for a regression if the helper is moved into
  status generation; retain the existing 181-day warning assertion.
- Browser/manual check: card with the supplied snapshot must have one `.freshness-field`, no separate
  `.patch-age-field`, and no duplicated “Last built” line.

## 2. One patch-count disclosure control

### Current behavior / source

`patchField()` emits `Patches: 21` and then a second `<details>` whose summary is
`Show the 21 patch names` (`docs/portal.js:535-542`). The current CSS separately styles
`.patch-details` (`docs/index.html:15`). This is the redundant count-plus-toggle the owner called out.

### Proposed design (exact changes)

Change **`docs/portal.js:patchField()`** to emit one control:

```js
function patchField(article,record){
  const patches=patchList(record);
  if(!patches){field(article,'Patches','Not recorded');return;}
  const all=el('details',undefined,'patch-details');
  all.append(el('summary',patches.length+' '+(patches.length===1?'patch':'patches')));
  const list=el('ul');
  for(const name of patches) list.append(el('li',name));
  all.append(list); article.append(all);
}
```

The visible control is therefore exactly `21 patches`; opening it reveals the names. For zero patches,
use `0 patches` and no empty list (or a short `No patches recorded in this release.` line). For a missing
record, retain the explicit non-folded `Patches: Not recorded` text. The summary is a native `<summary>`
with the existing 44px target and keyboard/focus behavior; no custom click handler is needed. Remove or
narrow only CSS that assumes a separate preceding paragraph; keep `.patch-details` list styling.

### Test impact

- In `tests/portal_contracts.cjs`, add a source/contract assertion for `patches.length+' '+...` and
  that the old `Show the '+patches.length+' patch names` string is absent. If a DOM fixture is added,
  assert exactly one `details.patch-details` per patch list and its `summary.textContent` is `21 patches`.
- Existing `patchList()` and release-record contracts remain valid. Add plural coverage for one and zero.
- Accessibility check: native details must open with Enter/Space and have no duplicate “Patches” label.

## 3. CCleaner: icon plus “Coming soon” disabled card

### Evidence and current behavior

- `src/targets.json:682-705` has `id: ccleaner`, `enabled: false`, package
  `com.piriform.ccleaner`, `poll: false`, and `max_patch_age_days: 180`.
- The target is deliberately omitted by `src/etc/status.py` (`enabled = [t for t in targets if
  t.get('enabled')]`, `src/etc/status.py:410`), and by `src/etc/pagegen.py:27`; this is correct. Do not
enable it or put it into the Obtainium import.
- `docs/assets/logos/ccleaner.png` exists. The official-source/provenance record identifies it as
  the 28 Oct W16w owner-supplied Google Play tile, but the current `LOGOS` set in `docs/portal.js`
  omits `ccleaner` (`docs/review/ICON-PROVENANCE.md`, 28 Oct sections; `docs/portal.js:13`).
- Disabled targets do still render: `appsPanel()` creates an article for every target and currently
  branches at `docs/portal.js:589-590` with badge `Disabled` and the exact text
  `Not eligible for new builds. Existing release history is available on GitHub.`

### Proposed design (exact changes)

1. In **`docs/portal.js`**, add `'ccleaner'` to `LOGOS`. `organizePanel()` already maps it to
   `assets/logos/ccleaner.png` and removes the image on load error; no new image loader is needed.
2. In the disabled branch of **`appsPanel()`**, replace the badge text with `Coming soon`. Use:
   `Not eligible for new builds. Existing release history is available on GitHub.`
   Keep one minimal link, `Release history`, to the repository release archive
   (`WEB+'/releases'`) if the owner wants the sentence actionable. Do not add provider links, an APK
   button, an Obtainium entry, or a workflow dispatch link. A safe implementation is an `el('p',...)`
   plus one `a` made through the existing `safeLink()`/`link()` helper; all visible copy remains
   `textContent`-based.
3. `src/targets.json`, `src/etc/pagegen.py`, `src/etc/status.py`, and `docs/index.html` generated
   catalog need no functional change. `appGroup()` already places `ccleaner` under Everyday
   essentials. Do not hand-add it to the generated `CATALOG` because disabled targets are intentionally
   absent from the Obtainium catalog.

Suggested disabled card text:

```text
[CCleaner icon]  CCleaner                         Coming soon
Not eligible for new builds. Existing release history is available on GitHub.
Release history
```

### Test impact

- Extend `tests/portal_contracts.cjs` to assert `LOGOS` includes `ccleaner`, disabled rendering uses
  `Coming soon` rather than `Disabled`, the old sentence remains (or its linked equivalent), and no
  `Open in Obtainium`/workflow-dispatch path is introduced.
- Add a target fixture asserting CCleaner remains `enabled === false`, `poll === false`, and absent from
  the generated catalog/import. Existing target-count and disabled-target tests should continue to pass.
- Add a visual/manual fallback test by temporarily making `assets/logos/ccleaner.png` unavailable:
  the card must retain the `CCleaner` heading and monogram, not become empty. Keep `img.alt=''` because
  the adjacent heading names the app and the image is decorative; the monogram container remains
  `aria-hidden=true`.

## 4. “Needs you” action UI: history, what exists, and safe design

### What the records actually establish

I found **no explicit earlier owner pitch for a button/action UI on the Pages site** in the requested
review records, knowledge files, council files, W17 brief, OPEN-WORK archive, KT/SESSION files, or the
clone's all-ref Git history. The requested command also yields no `Needs you`/portal/button commit
subject that establishes such a pitch. This is an important limitation: do not attribute a site action
proposal to the owner without a source.

The closest, sourced items are distinct:

- **23 Oct 2026 (W16 brief):** the owner asked for one daily `Needs you` issue and plain app cards;
  the record says the page should remain a shelf, not that it should write to the issue
  ([historical W16 brief](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/history/W16-BRIEF.md#L65-L95)).
- **24 Oct 2026 (W16d):** the implemented owner action is an issue comment, with exact grammar
  `take N-xxxxxx`, `drop N-xxxxxx`, `hold N-xxxxxx`; later W16j records group commands, `yes all`,
  `take G2`, `keep`, and `take N-xxxxxx except "Name"` ([session record](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/history/SESSION-2026-10-24.md#L95-L115);
  [Needs you parser](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L55-L70)).
- **25 Oct 2026, 22:13 IST:** the documented Pages UI pitch was **owner-only “Add an app”**, not
  Needs you. Its brief explicitly says Pages stays public/read-only, holds no token and calls no write
  API; the planned link opens a GitHub workflow dispatch form, where GitHub permissions—not Pages—limit
  who can run it ([W17 brief](https://github.com/govinda-rajulu/patch-factory/blob/main/docs/review/W17-BRIEF.md#L1-L30)).
- **What exists now:** `.github/workflows/needs-you.yml` renders/edits one standing issue; the renderer
  embeds stable `N-xxxxxx` metadata in HTML comments; the comment workflow accepts only owner comments
  on an issue titled `Needs you`; `apply_effect()` may dispatch `add-target` or `explore` after a
  validated owner `take` ([renderer metadata](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L692-L702),
  [effects](https://github.com/govinda-rajulu/patch-factory/blob/main/src/etc/needs_you.py#L767-L805),
  [owner/comment contracts](https://github.com/govinda-rajulu/patch-factory/blob/main/tests/needs_you_contracts.py#L207-L277)).
  The portal itself has no Needs you issue link or action controls; its existing read-only checks reject
  write paths such as `Authorization`, `method:`, and `/dispatches` ([portal contract](https://github.com/govinda-rajulu/patch-factory/blob/main/tests/portal_contracts.cjs#L44-L52)).

### Minimal safe design

**Phase 1 (recommended, no workflow/schema change):** add one `Open Needs you` link in the Watch tab,
next to the existing “Open failure issues” section, targeting the standing issue
`https://github.com/govinda-rajulu/patch-factory/issues/233`. Under it, render one plain instruction:

```text
Owner action happens on GitHub: comment `yes all`, `take G2`, `take N-xxxxxx`, `drop N-xxxxxx`, or `hold N-xxxxxx`.
```

Implement in **`docs/portal.js:watchPanel()`** with a constant such as `NEEDS_YOU_ISSUE = WEB+'/issues/233'`
and the existing `link()` helper. Keep it visibly a link, not a fake button. If issue number stability is
not guaranteed, add a read-only `needs_you` URL/number field in `src/etc/status.py` and consume it only
after validation; do not discover arbitrary issue URLs from untrusted body text.

Do not use `?body=` or a guessed “new comment” URL: GitHub has no general public GET endpoint that
reliably pre-fills a comment on an existing issue, and a new-issue prefill could misroute an owner reply.
A future per-item affordance may deep-link to the issue and its stable comment anchor, but it must still
show the exact grammar and require the owner to press GitHub's own Comment button.

**Phase 2 (only with owner approval):** status data may expose a validated, current Needs you issue URL
and item IDs, while the portal renders read-only rows with `Open issue` links. Never add a token, POST,
workflow dispatch, GitHub API write, clipboard auto-submit, or client-side decision ledger. Any “Take”,
“Drop”, or “Hold” control on Pages would be misleading unless it merely opens GitHub and leaves the
actual owner comment to GitHub.

### Test impact

- `tests/portal_contracts.cjs`: assert the link is exact-repository `issues/233`, the instruction includes
  the supported grammar, and source still contains no `Authorization`, write `method:`, `/dispatches`,
  `localStorage`, or `innerHTML`.
- `tests/needs_you_contracts.py`: no behavior change. Keep parser tests for group/item grammar and
  owner-only comments; do not change `apply_effect()` or workflow permissions for a link-only portal.
- Manual/accessibility check: link has an unambiguous accessible name (`Open Needs you issue`), opens a
  normal GitHub page in a new tab with `noopener noreferrer`, and does not imply that clicking it made a
  decision.

## 5. Short UX cleanup list

1. **Ship the four card changes together:** the current `Patch age` plus `Last built` duplication and
   `Patches: N` plus `Show the N patch names` duplication are the most visible repeated UI. Remove the
   obsolete CSS/strings after the JS change.
2. **Turn “available on GitHub” into one real link:** the disabled-card sentence currently promises a
   destination but has no anchor. Use one `Release history` link for CCleaner; avoid provider, workflow,
   and download links on a disabled card.
3. **Clarify status vocabulary:** “Coming soon” is a lifecycle label; “Not eligible for new builds” is
   the reason. Keep them as badge + sentence, not two badges or “Disabled / Coming soon”.
4. **Avoid redirect/dead-surface regressions:** retain the single app-shelf tabs; `docs/status.html` and
   `docs/status.js` are already gone and contract-tested. Do not add a second status page or a fake
   redirect. Keep footer `Release archive`/`Workflows` as global destinations, while card links remain
   contextual (`Install APK`, `Full release notes`).
5. **Remove dead portal code only in a separate cleanup:** `patchText()` appears unused by the current
   renderer. Confirm with a contract/search pass before deleting; do not mix it into the behavior change.
6. **Fix provenance wording separately:** `docs/review/ICON-PROVENANCE.md` contains dated historical
   sections that say CCleaner gets no tile and later say it ships. Preserve history, but add a short
   “current inventory supersedes earlier sections” note so readers do not treat the records as
   contradictory current state.
7. **Accessibility/text rule:** continue creating all runtime labels with `el()`/`textContent`; do not
   introduce `innerHTML`, markdown-as-HTML, or icon-only controls. Native `<details>/<summary>`, visible
   focus, 44px targets, `aria-live` status, and the existing decorative `alt=""` policy are sufficient
   for these changes. Test both light/dark and reduced-motion CSS after replacing the patch fold.

## Plain-text mock of the proposed card

```text
CCleaner                                      Coming soon
[local CCleaner icon]
Not eligible for new builds. Existing release history is available on GitHub.
Release history

YouTube                                        21.36.45
Freshness: patch bundle updated 1 day ago · last built Oct 30, 12:06 AM (32 h ago)
21 patches                                      >
  (closed; opening lists the 21 patch names)
Provider: Morphe
Bundle: v1.49.0
[Install APK]
[What changed & older versions]
```

For a card with an old bundle, the single row changes to:

```text
Freshness: patch bundle updated 166 days ago · last built Oct 30, 12:06 AM (32 h ago)
WARNING: within 14 days of the 180-day advisory limit.
```

For an exceeded bundle:

```text
Freshness: patch bundle updated 181 days ago · last built Oct 30, 12:06 AM (32 h ago)
WARNING: over the 180-day advisory limit. Build gates still decide.
```

## Risks and limits

- **Staleness semantics:** “near” needs a fixed documented threshold; this memo recommends 14 days
  before the per-target cap. The cap remains advisory and must not silently become a build gate.
- **Locale:** `stamp()` uses `toLocaleString`; exact month/day order varies by browser locale. If the
  owner requires `Oct 30` everywhere, pass an explicit `en-US` locale and test it; otherwise tests
  should assert semantic text, not one locale's punctuation.
- **Status freshness:** the supplied snapshot is a point-in-time artifact. Live GitHub/API data can
  differ, and the public page may be rate-limited; no empty/error state should be interpreted as a
  successful build.
- **CCleaner availability:** disabled targets are intentionally absent from status and Obtainium; the
  icon and “Coming soon” card must not imply a build or a released APK. The onboarding record says no
  CCleaner release was ever published.
- **Needs you write boundary:** a Pages deep link cannot authenticate or safely submit an owner action.
  Do not add a token, browser credential, GitHub write endpoint, workflow dispatch, or a URL that creates
  a new issue by accident.
- **Unverified historical pitch:** no exact “Needs you action UI on the site” source was found in the
  requested records/history. The conclusions above distinguish the documented issue-comment grammar and
  the separate W17 Add-app Pages pitch from that unverified premise.
