# Patch-factory automation map (live `main`)

Read-only design review of (assistant sandbox), plus the supplied
workflow inventories/status snapshot at (assistant sandbox).
Evidence is `file:line`; the compact history JSON is one line, so history citations are
`history-*.json:1` plus a run id.

## Decision summary

| Item | Current state | Exact proposal | Size/risk | W16y |
|---|---|---|---|---|
| Watched providers | 10 `watch` rows; 8 `drop_providers`; watched rows stay quiet until app-version-ready. Needs you runs daily. | Non-actionable monthly digest in Needs you on the first UTC run/month; never auto-adopt. | S/low | Yes |
| Patch age | Caps are 60 days, except Truecaller 120; resolve only logs age information. Portal/status omit patch age. | Set all to 180; expose release age and advisory warning in status and cards; never block. | S/low | Yes |
| Pin health | Real builds check exact `version_code`; no scheduled read-only existence check. | Weekly Nightly read-only listing check for Instagram/Facebook/MX Player/Reddit; emit `PIN_STORE_OK`/`PIN_STORE_MISSING`; existing Failing issue routing. | M/medium | Small slice |
| Tools/models | Tooling watch PRs pinned-tool changes and reports Morphe; council probes models and falls through missing IDs, but does not update seats/changelogs. | Live catalogue + bounded probes -> deterministic best-free proposal PR only; no auto-merge/secrets/config writes. | L/high | Later (catalog report can be W16y) |
| Fallbacks | Check new patch is scheduled; Batch is dispatch-only; Nightly is not a build. Fallbacks are at most 2 extra attempts, but not prefiltered. | W16y telemetry/tests only; later optional conservative eligibility preflight. | S now/M later | Telemetry only |

## 1. Watched providers

### Current state / owner view

* The ledger has ten `watch` rows (`src/patches/DECISIONS.json:804-933`): `photos/RookieEnough/De-Vanced`, `truecaller-combo/dunecache/oyasumi-patches`, `facebook/andrewliang25/morphe-patches`, `facebook/SapitoSucio/FroggoMorphePatches`, `instagram/kveld9/kveld-extra-morphe-patches`, `hotstar/Paresh-Maheshwari/paresh-patches`, `mxplayer/mich111discord/MightyMichs-Patches`, `telegram/mich111discord/MightyMichs-Patches`, `telegram/ch3thanhs/stylus`, and `telegram/rahul9999xda/morphe-patches`. It has eight `drop_providers` rows (`src/patches/DECISIONS.json:935-960` and following rows): Instagram FoxxoOwO, crimera, dawidd612, Dreaming-Codes, giaaaacomo; Reddit Santodan and Mubelotix; Telegram newuser7171.
  `decisions.provider_state` defines dropped providers as `drop`, watched as `watch`,
  otherwise no state (`src/etc/decisions.py:44-53`).
* Needs you reads provider state while scanning the community index. It drops `drop`
  entirely and suppresses `watch` unless its newest listed app version is ready
  (`src/etc/needs_you.py:453-472`). A ready watched row is rendered as “you took it; it
  now fits our version” (`src/etc/needs_you.py:482-504`, `:907-915`). This is not
  adoption: it does not edit `targets.json`.
* Provider watch is name-only and explicitly has no patch-selection/build/publication
  authority (`src/etc/provider_watch.py:24-31`); it says no selection/baseline was
  modified (`src/etc/provider_watch.py:217-220`). It runs Mondays
  (`.github/workflows/agent-watch.yml:1-8`).
* The owner-facing merge is one standing Needs you issue. It runs daily at `04:59 UTC`
  (`.github/workflows/needs-you.yml:1-8`), fetches newest artifacts and renders them
  (`.github/workflows/needs-you.yml:39-59`). Empty output is a quiet OK; actionable
  rows are grouped with comment commands (`src/etc/needs_you.py:831-855`, `:887-902`).

**Today in plain words:** the owner sees the daily standing issue's ordinary Selection,
community, failure and FYI sections. A watched provider remains invisible while behind
our app version; a ready one can become a normal review choice and still requires an
owner `take`. Dropped providers never appear. The supplied bundle does not contain the
live Needs you body, so exact current visible rows are not verifiable.

### Exact change

Add `watched_provider_digest(memory, bundles, targets, now)` to `src/etc/needs_you.py`.
For each ledger watch row, output target/repo, taken names (and exceptions), decision date,
and one of `WAITING_FOR_APP_VERSION`, `READY_FOR_REVIEW`, `NOT_IN_INDEX`. Render it only
when `now.day == 1`, under:

```text
## Watched providers — monthly digest (review only; never auto-adopt)
- facebook / andrewliang25/morphe-patches — 4 taken names; WAITING_FOR_APP_VERSION (provider 577; ours 584); decision 2026-10-25.
```

Lines must contain no `N-xxxxxx`, `take`/`keep` grammar, `action=explore`, or ledger effect.
If “first run” must mean first *successful* run after a missed day, add and preserve a
`<!-- watched-provider-digest: YYYY-MM -->` marker in `deliver()`; that is larger and can
follow W16y.

**Tests:** extend `tests/needs_you_contracts.py`: day 1 includes the heading/rows, day 2
omits it, no digest line parses as a command, not-ready watch stays suppressed, ready watch
gets `READY_FOR_REVIEW`, and dropped provider never appears. Keep
`tests/decisions_contracts.py` for ledger semantics. **S/low; W16y yes.**

## 2. Patch age: 180-day warning only

`src/targets.json` carries 60 (`:11-12`, and Facebook `:273-278`) and Truecaller 120
(`src/targets.json:132-137`). `resolve.sh` loads `MAXAGE` (`src/build/resolve.sh:17-20`),
computes release age (`:35-42`) and prints an information line after the mark
(`:42-50`); the comments explicitly say age is not a disqualification and applied-count
verification decides (`:42-49`). README generation calls caps advisory
(`src/etc/readmegen.py:45-57`).

`status.py` app rows currently contain release/last-build/check data but no max age or
release age (`src/etc/status.py:383-407`). The supplied status snapshot has build age and
release timestamp (Facebook example `status.json:135-169`), but no patch-age warning.
Portal cards render version, patches, provider, bundle and last built
(`docs/portal.js:565-583`); badges currently cover fallback/build/new only
(`docs/portal.js:555-563`). Pagegen generates the catalog note, not cards
(`src/etc/pagegen.py:22-40`).

### Exact change

1. Replace every `max_patch_age_days` with `180` in `src/targets.json`; regenerate README
   (`python3 src/etc/readmegen.py`). Do not change `max_app_version`.
2. Add `patch_age_days(published_at, now)` to `src/etc/status.py`; add app fields
   `max_patch_age_days`, `patch_age_days`, `patch_age_warning`. Use status generation UTC
   time and release `published_at`; invalid/missing release yields `None`/false. Never add
   this warning to `BAD`, headlines, candidate selection, release gates or fallback logic.
3. Add `patchAgeField(article,target,statusRow,top)` in `docs/portal.js` after version/patch
   fields. Render `Patch age: N days / 180-day limit — WARNING (advisory; build gates still decide)`
   when over limit, and `unknown` when timestamp/status is unavailable. Never hide Install.
   Run pagegen after JS changes to refresh its portal asset digest; no hand-edited card data.
4. Keep resolve's informational line, changing wording to `WARNING (advisory only)`.

**Tests:** `tests/status_contracts.py` for 179/180/181, invalid date, and warning not
changing success/failure; `tests/portal_contracts.cjs` for old-release display and install
remaining; `tests/pagegen_contracts.py` for catalog/source separation; shell contract that
age path has no `exit`/`DISQUALIFIED`. **S/low; W16y yes.**

## 3. Weekly read-only pin-store check

The selected targets' fields are Facebook (`version_code` + `max_app_version`,
`src/targets.json:273-278`), Instagram (`:320-325`), Reddit (`:387-392`) and MX Player
(`:498-503`). Real source preparation records package/version/code and rejects a mismatched
code (`src/build/source_inputs.py:60-76`, `:154-166`). APKMirror's `get_apk` parses the
variants table and passes `PF_PIN_CODE` to `variant_pick.py` (`src/build/utils.sh:601-642`);
source download invokes APKMirror/APKPure and can try the other store
(`src/build/source_download.sh:8-37`). These are download/build paths, not a read-only
existence API. Qualify only runs after successful Check/Manual/Batch publications
(`.github/workflows/qualify-baselines.yml:1-5`, `:35-51`) and does not check stores.

### Exact smallest design

Extend **Nightly watch** rather than Qualify. Add a second weekly cron to
`.github/workflows/watch.yml` (e.g. `41 1 * * 1`) and a `pin-health` job gated on that
exact `github.event.schedule` value. It should checkout without credentials, use no secrets,
not start store containers, and never download an APK.

Add `src/build/pin_store_check.py`:

1. Load enabled targets and select only rows with `version_code` or `max_app_version`; the
   current expected set is the four named targets.
2. Factor the page/variant-list portion of `get_apk` into a pure `list_store_variants`
   helper in `src/build/utils.sh`, and factor APKPure page-version extraction from
   `get_apkpure`. The checker follows listing/release HTML only, never final binary URLs.
3. Require exact `version_code` row when present and report the configured max version's
   availability/ordering (a max is a ceiling, not an exact pin). Emit only bounded lines:

   ```text
   PIN_STORE_OK target=facebook store=apkmirror version=584.0.0.51.56 code=475817393
   PIN_STORE_MISSING target=instagram store=apkmirror reason=version_code_not_listed
   ```

   Transport/parser failure is unknown and nonzero, never OK. Redact URLs/cookies/error
   text, cap output, and upload a small JSON/log artifact. Do not edit config/baselines.

A missing result fails Nightly. Existing routing already covers it: status wakes on Nightly
(`.github/workflows/status.yml:13-18`), calls Notify (`:82-90`), and Notify maps watch.yml
to `7. Nightly watch` (`.github/workflows/notify-failure.yml:28-43`). Thus the standing
`Failing: 7. Nightly watch` issue gets the failure and next green run closes it; no new
issue writer is needed.

**Tests:** add `tests/pin_store_check_contracts.py` for exact code/max-version present/missing,
unreadable transport, unrelated target skip, URL/token redaction. Add workflow contracts for
weekly gate, exact output markers, no `wget`/binary transfer/final URL/secrets, plus a normal
`get_apk` download regression. **M if shared refactor, S if isolated adapter; medium
HTML-drift risk. W16y can land isolated checker/tests.**

## 4. Tools, patcher and council model self-updating

### Current state

Tooling watch reads `TOOLING.sha256`, picks newest non-draft release (pre-releases included),
verifies bytes/digest and only rewrites with `--apply` (`src/etc/tooling_watch.py:1-16`,
`:67-119`). Its daily workflow turns a diff into a branch/PR, dispatches Validate, or posts
an issue if PR creation fails (`.github/workflows/tooling-watch.yml:1-6`, `:30-65`).
`morphe-desktop` is deliberately unpinned: every build uses latest stable and the report
shows stable versus newest/pre-release (`src/etc/tooling_watch.py:10-15`, `:123-149`).
`upstreams.json` records Morphe desktop as that latest-stable source
(`src/etc/upstreams.json:3-12`). Dependabot covers `/` and every composite-action directory,
weekly Monday, groups minor/patch and leaves majors individual; no auto-merge
(`.github/dependabot.yml:1-21`).

Council provider catalogue endpoints/secrets are in `src/council/council.py:49-78`.
Seats/models/discovery/backups are in `src/council/seats.json:5-48`, `:51-126`,
`:129-242`, `:245-356`; the NVIDIA Nemotron seat lists Ultra then 3.5 Super VL
(`src/council/seats.json:93-126`). `available_models()` fetches live catalogues where
available and candidates prioritizes listed models then up to two discovery matches
(`src/council/council.py:536-569`). Actual 404/410 (or model-named 400/422) is
`ModelMissing` (`:679-699`); `run_seat()` remembers it, tries later models/backups and emits
`UNAVAILABLE no listed model answered` if none works (`:850-934`). Onboarding emits the same
phrase (`src/council/onboard_review.py:134-174`).

Sunday probe already checks every listed model and configured alternate and posts “Gone or
refused”/“New in the catalogues” (`src/council/council.py:2045-2089`); Council schedules
include two daily desk slots (`.github/workflows/council.yml:11-18`), and Sunday morning
selects probe (`src/council/council.py:628-639`). This is report/fallback behavior, not
config replacement or changelog adoption.

### Exact safe design

Add `src/council/model_watch.py` (pure module + CLI) and a weekly
`.github/workflows/model-watch.yml` after the Sunday probe:

* Make one bounded authenticated catalogue GET per unique provider; check every seat model,
  backup and discovery candidate. Catalogue absence is `CATALOGUE_MISSING`; direct 404/410
  is `MODEL_UNSERVED`; 429/5xx/timeout is `UNKNOWN_BUSY`, never deprecation.
* Treat a model as free only with provider metadata or an allowlisted pricing document
  proving free/zero; never infer from `:free`. Require input budget >= seat
  `max_input_chars`, JSON/reasoning compatibility and stable/pre-release evidence.
* Read only allowlisted changelog/release URLs (add `changelog` metadata to
  `src/etc/upstreams.json`); record feature changes as proposals, not executable instructions.
* For a missing/deprecated model, deterministic rank is same provider/API, free proof,
  adequate context, stable over preview, required features, then model id. If no proof,
  emit `NO_SAFE_REPLACEMENT` and do not edit seats.
* A trusted step may create a branch/PR changing only `src/council/seats.json`, upstream
  metadata and `docs/council/PROVIDERS.md`. Never alter secrets, workflow permissions or
  arbitrary config; never push main/merge/auto-merge. Follow Tooling watch's PR pattern
  (`.github/workflows/tooling-watch.yml:34-56`), run Validate, and use one bounded issue if
  PR creation fails.
* Rate-limit: one catalogue GET/provider/run; at most two probe POSTs per provider/model,
  serialized per provider; use existing PACE values (`src/council/council.py:80-87`), cap
  9 providers/60 requests/15 minutes, honor Retry-After, cache per run, redact keys from
  artifact/PR/log. Human verifies free terms, context, JSON behavior, changelog and seat fit.

**Tests:** `tests/model_watch_contracts.py` for catalogue lag vs 404/410 vs busy, free proof,
deterministic ranking, context rejection, changelog allowlist, redaction, request limits and
secret/config write allowlist; extend council contracts for `NO_SAFE_REPLACEMENT` and preserving
jobs/personas/backups; workflow contract forbids merge and checks exact changed-file allowlist.
**L/high; later.** W16y-safe slice: add catalogue status to existing Sunday probe and test it,
without config writes or PR generation.

## 5. Fallback smokes and ineligible-fallback cost

Check new patch is scheduled twice daily (`.github/workflows/ci.yml:1-14`) and calls reusable
Manual Patch for selected targets (`.github/workflows/ci.yml:211-230`). Supplied history has
scheduled Check runs including `41011195629`/`40931823093` (`history-scheduled.json:1`). Batch
Patch is workflow-dispatch only and fans into Manual Patch (`.github/workflows/batch-patch.yml:1-5`,
`:40-55`); no Batch run appears in the scheduled inventory (`history-scheduled.json:1`).
Nightly is daily evidence collection, not a build (`.github/workflows/watch.yml:1-55`); its
history has e.g. `41021713094` success and `40649522527` failure (`history-nightly-watch.json:1`).
Thus Nightly does not automatically smoke fallback builds today.

`build_attempts.py` tries primary resolution first, then other primaries and `fallback:true`,
with at most `PF_MAX_FALLBACKS` default 2 extra attempts (`src/build/build_attempts.py:1-20`).
Pinned/`fallback:false` targets are one attempt (`:74-83`). Later attempts reset the checkout,
pin overrides, clear prepared inputs and may reuse lazy store services (`:204-230`); success
writes `.fallback`/`PROVIDER_FALLBACK` (`:230-245`).

`resolve.sh` skips fallback candidates during normal election (`src/build/resolve.sh:25-35`),
and no viable primary exits (`:104-109`). A fallback is not prequalified there: controller
pins it and launches a fresh build, whose resolver failure is surfaced
(`src/build/build.sh:61-100`). Exact version-code targets cannot step down when stores fail;
unavailable primary/qualified fallback exits (`src/build/build.sh:211-224`). Therefore an
ineligible fallback is bounded but not free: it may spend another patcher/bundle resolution,
store listing/download and patch attempt before failing. The history bundle cannot establish
which target used one or its seconds/requests because it has no jobs/steps/logs.

### Recommendation

W16y: no selection change. Add bounded attempt summary to build evidence/status and tests for
max three total attempts, no attempts for `pin`/`fallback:false`, reset-before-later-attempt,
and fallback marker only after later success. Later (M), add cached
`src/build/fallback_eligibility.py`: return `ELIGIBLE`, `INELIGIBLE`, or `UNKNOWN` against
max-version/exact-code, never skip on UNKNOWN, and leave order/cap unchanged. **Telemetry S/low;
eligibility M/medium; W16y telemetry/tests only.**

## Real limitations

1. History files are compact workflow-run inventories, not jobs/logs/artifacts; fallback use
   and per-target cost are unverified.
2. The live Needs you issue body was not supplied; owner-view statements are renderer behavior,
   not exact current rows.
3. Store pages and live model catalogues were not fetched; proposed checkers treat parser/
   transport uncertainty as unknown/failure, never OK/deprecated.
4. Supplied status was generated at `2026-10-30T08:37:19Z` (`status.json:723-734`) and has
   build ages/release timestamps, not patch-age fields; examples are Facebook
   (`status.json:135-169`), Instagram (`:219-258`), MX Player (`:434-468`) and Reddit
   (`:518-552`).
