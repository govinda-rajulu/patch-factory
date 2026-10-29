# Decision review, 29 October 2026 (packet W16x)

Read-only review of the standing owner decisions and their downsides, by a scoped review agent (Anthropic Claude models); nothing here changes a decision. Owner questions are at the end; the open ones are listed in OPEN-WORK.md.

Scope: read-only review of `src/patches/DECISIONS.json` (all 114 name rows, 10 `watch` rows and 8 `drop_providers` rows), the W16w decision sheet/owner rules, adoption policy, targets, retired builds, switch audit, signer note, schedules, W16x diff (`9fedca21..HEAD`), and the 28-Oct owner-run records. Severity is operational/user impact if the standing decision remains unchanged, not a judgement that the owner was wrong. **Every HIGH below was re-checked against the current implementation.**

## Ranked findings (HIGH first)

### H1 — Hard store/version pins can become a stale, silent shelf (and the fallback version door is one-way)

**What / where.** Instagram is constrained to `452.1.0.53.64`, APKMirror build `385811006`, with no candidate pin but an exact `version_code` (`src/targets.json:318-382`, especially `:323-369`). Facebook is fixed to `584.0.0.51.56`, code `475817393` (`src/targets.json:271-315`); Reddit is capped at `2026.41.0` (`:385-435`); MX Player at `1.93.4` (`:496-546`). Exact pins are intentionally non-step-down: `build.sh` refuses a lower version when `version_code` exists (`src/build/build.sh:293-305`), and the source preparation path does the same (`src/build/source_inputs.py:156-179`).

**Why / evidence.** The daily poll only asks whether a configured provider bundle is newer than the newest local release (`src/etc/poll.sh:14-24,57-105`); it does not test whether the pinned store file still exists. The daily plan consequently builds only changed targets (`src/etc/daily_plan.py:72-97`). If APKMirror removes the pinned Instagram/Facebook/Reddit file while the provider has not changed, no store check runs, no build failure occurs, and the last release can remain stale with no targeted alert. A store failure is visible only when that target is eventually built; the run's generic failure issue/status machinery is in `.github/workflows/status.yml:1-18,60-90` and `.github/workflows/notify-failure.yml:10-18`, not a pin-removal alarm.

The owner-run gives the concrete cost: the wrong Amazon Music provider version (`2.36.1`) selected APKMirror's unrelated `2.8.1` (2013) file; before W16x the signer pin was the only thing that stopped it (`docs/review/HANDOVER-2026-10-29-W16x.md:12-17`; `src/build/PUBLISHERS.json:5-10`). W16x's guard now rejects that downgrade, but it also makes every lower-version fallback/publish path refuse once a newer release is on the shelf: `publish_guard` compares the current version to the newest published app version and refuses lower versions (`src/build/release_notes.py:174-193`). The W16x KT records the real failure mode: a fallback on a newer version is a one-way door because the shelf then refuses the older primary (`docs/review/KT-2026-10-28.md:69-71`).

**Likelihood / severity / confidence.** Medium likelihood (stores do remove or reshuffle files); **HIGH** impact for stale/security-sensitive apps because the owner may keep installing an old build and receives no alert until a later provider-triggered build. High confidence from the poll and build paths. The one-way door is certain once a higher-version fallback release exists.

**Cheaper/safer alternative.** Keep the safety pin, but make a cheap scheduled *read-only pin health poll* for every target with `version_code`/`max_app_version`: check the selected store listing and emit `pin_state=present|missing|unknown`; missing/unknown should create the existing standing failure issue without publishing or changing the pin. Never auto-select a different version.

**SAFE-NOW mitigation (does not change the decision).** Add a store-health step to `ci.yml`'s Plan after `daily_plan.py` that calls a new read-only checker over the exact target pin (same `PF_PIN_CODE`, SDK, arch/dpi filters) and fails with a fixed `PIN_STORE_MISSING <target> <version/code>` line; add that line to `status.py`'s fixed reason parser. This is a code change requiring tests; it does not change pins or publication. Without owner approval, do not silently change the store source or version. **Owner needed** to approve the additional daily store traffic/alert semantics.

### H2 — `amazonmusic` paid-tier takes encode a known account-ban risk

**What / where.** The owner took `Unlimited track skipping`, `Unlock Unlimited`, and `Rename shared permissions` (`src/patches/DECISIONS.json:454-472`), and explicitly put `amazonmusic` in `paid_ok_targets` (`src/patches/ADOPT.json:50-58`). The target says “Test account only” (`src/targets.json:626-651`). The onboarding record says the throwaway account was banned while those paid patches were on (`docs/review/onboarding/amazonmusic.md`, W16x addition); the T1 build still failed closed on the publisher certificate ((owner run evidence, not in the repo), `amazonmusic` row (batch and check failures)), so this is a real policy risk even though no current APK shipped.

**Why.** `selection_watch.classify` exempts paid words for targets in `paid_ok_targets` (`src/etc/selection_watch.py:146-158`), so a later provider name containing `unlock`/`premium` can become an adopt candidate rather than waiting for owner review. The standing decision therefore normalizes a known account-enforcement risk into an automatic-selection permission. The current build does correctly refuse an unrecognized publisher certificate (`src/build/build.sh:264-267`; owner run showed `PUBLISHER_CERT_UNREADABLE`), but that protects APK provenance, not Amazon's account-ban detection.

**Likelihood / severity / confidence.** Account enforcement has already happened once; likelihood **high** if tested with a real account, **HIGH** severity (account loss/lockout), high confidence in the repo evidence. Runtime ban causality is recorded by the owner, not independently reproduced here.

**Cheaper/safer alternative.** Keep the owner decision only as a manual, throwaway-account experiment; do not let Selection watch auto-adopt future paid Amazon names. Prefer privacy/ad-removal patches without entitlement bypass.

**SAFE-NOW mitigation.** None that preserves the current `paid_ok_targets` decision: changing `paid_ok_targets` or adding an Amazon-specific confirmation gate is an owner policy change. A non-behavioral warning in generated onboarding/status can be added now, but it cannot prevent adoption or a ban. **Needs owner.**

### H3 — Turning Signer pin off on Android 10 removes pre-install authenticity checking

**What / where.** The owner rule is to untick Obtainium's Signer pin only on Android 9/10 and keep it on for Android 11/12 (`docs/review/OBTAINIUM-SIGNER-2026-10-27.md:14-27`). The main phone is Android 10 (`:18-25`). The note's source analysis says Obtainium requests only `GET_SIGNING_CERTIFICATES`; Android 9/10 therefore returns no certificate, while Android 11+ reads it (`:5-12`). With no allowed hash, Obtainium proceeds without warning (`:27`).

**Why.** This is not merely a UX workaround: Android 10's install path loses the client-side check that the downloaded APK matches the project's configured signer. Android still enforces same-signer updates after an app is installed (`:25`), but that does not authenticate the first download or a replacement after uninstall. A malicious/replaced APK can therefore reach the Android install prompt without Obtainium's signer warning. Keeping the pin blocks every install/update instead, so this is a genuine security-versus-availability tradeoff.

**Likelihood / severity / confidence.** Exploit likelihood unknown; consequence **HIGH** (supply-chain/install authenticity), high confidence in the API-version analysis recorded in the signer note. No live phone retest was available in this lane.

**Cheaper/safer alternative.** File the upstream Obtainium fix to request both `getSigningCertificates` and `getSignatures` on API <30 (`OBTAINIUM-SIGNER-2026-10-27.md:29-32`), then restore the pin. Until fixed, distribute the no-pin JSON only to the Android 10 device and verify release SHA/signing certificate out of band before every install.

**SAFE-NOW mitigation.** No patch-factory code edit can make Obtainium read the certificate on Android 10. Keep `docs/obtainium.json` pinned for Android 11/12; prominently label `docs/obtainium-nopin.json` as Android-9/10-only (already generated by `src/etc/obtainium.py:80-83`). Owner must file/test upstream and perform the out-of-band hash check.

### H4 — Fallbacks are expensive idle paths, while safe publishing rules can strand recovery

**What / where.** Fallback candidates never compete in normal resolve; they are attempted only after primary failure (`src/build/resolve.sh:30-35`; `src/build/build_attempts.py:4-20,74-83`). Current fallback topology includes Instagram HushGram and oxbow (`src/targets.json:328-363`), Facebook De-Vanced (`:281-305`), MX MightyMichs (`:506-528`), Telegram rushiranpise (`:559-578`), and the newly added ES File rushiranpise fallback (`:229-251`; W16x diff). The W16x evidence records HushGram smoke failure because it lists only Instagram 453, while the target is pinned to 452.1, and MightyMichs failing its only MX 1.93.4 patch fingerprint (`docs/review/HANDOVER-2026-10-29-W16x.md:14-17` and `docs/review/OPEN-WORK.md:21-25`).

**Negative impact.** Manually smoking/watching a fallback that cannot satisfy the target pin spends provider-download, resolver and patch minutes and can make the status page red even when the published primary is healthy. The owner record shows this directly: HushGram advisory smoke failed, while piko succeeded ((owner run evidence, not in the repo), `smoke.instagram/hushgram` and `smoke.instagram/piko`); the W16x status red Instagram was later a nonpublishing oxbow smoke (`docs/review/OPEN-WORK.md:28-31`). A successful newer fallback publication is worse: `publish_guard` then refuses the older primary (`src/build/release_notes.py:174-193`), exactly the W16x wrong-call-108 scenario recorded in `KT:69-71`.

**Likelihood / severity / confidence.** High likelihood for currently idle Instagram and MX fallback smokes; **HIGH** for the version-door/phone-update consequence, medium for wasted minutes. High confidence from code and owner-run records.

**Cheaper/safer alternative.** Mark a fallback as *version-ineligible* until it lists the target's exact version/build; skip its automatic smoke/watch while retaining the candidate for a future provider release. Require a whole-target pin move before any fallback can publish a newer version.

**SAFE-NOW mitigation.** Add a preflight fast-fail before `build_attempts.py` dispatch: compare provider-supported versions from resolve metadata with target `max_app_version`/`version_code`; report `FALLBACK_INELIGIBLE` and do not download/patch. Keep `publish_guard` unchanged. This preserves “fallback exists” and “never publish downgrade,” but needs an owner-approved change to smoke scheduling (otherwise it changes which evidence is collected).

### H5 — The near-version guard can both refuse recoverable versions and accept a broad “same line” downgrade

**What / where.** W16x added `pf_near_version_safe` (`src/build/store_chain.sh:24-37`) and calls it from both normal build and source preparation (`src/build/build.sh:194-202`; `src/build/source_download.sh:25-33`). It accepts exact versions, a wanted version with the fetched version as a prefix, or any fetched/wanted pair sharing the first two numeric components; otherwise it emits `STORE_DOWNGRADE_REFUSED` and deletes the downloaded file.

**Why / evidence.** Amazon's `2.36.1 -> 2.8.1` refusal is correct and prevented a 2013 APK. Prime Video and Hotstar were deliberately accepted as same-release-line near versions (W16x handover). The heuristic is still not a release identity proof: `26.36.1 -> 26.36.0` accepts even if semantics changed; conversely a vendor may make a compatible release-line transition such as `4.1.x -> 4.0.x` where the first two components change and the guard falsely refuses. The code has no store build-code proof in this path unless a target has an exact `version_code` (variant picker only checks that configured row when available: `src/build/utils.sh:622-643`). No false refusal is recorded in W16x; this is a latent heuristic risk, not an observed outage.

**Likelihood / severity / confidence.** Medium likelihood as stores/provider version conventions change; **MEDIUM** severity (false refusal causes missed build; broad acceptance can make a wrong app version); medium confidence for unobserved cases, high confidence in the heuristic's shape.

**Cheaper/safer alternative.** Require reviewed version-family rules per target, or use a qualified exact version/build-code admission rather than first-two-component equality. Keep the hard refusal for unrelated versions.

**SAFE-NOW mitigation.** Add unit cases for each target's real version grammar and log the requested/fetched versions as a structured failure; do not loosen the guard without owner review. Exact heuristic replacement needs owner approval because it changes the “never silent downgrade” rule's acceptance boundary.

### M1 — `max_patch_age_days` is documented per target but is advisory only; old providers can remain selected

**What / where.** Targets set 60 days for nearly every app and 120 for Truecaller (`src/targets.json:11,38,64,100,136,196,225,277,324,391,444,473,502,555,594,632,660,688`). `resolve.sh` computes age and prints a plain informational line when over the cap (`src/build/resolve.sh:17-20,41-50`); its comment explicitly says age is not disqualification and the applied-count gate decides. `src/build/shadow_inputs.py:86` excludes `max_patch_age_days` from the resolved declaration. The owner rule also says provider age is advisory, never a kill switch (`docs/council/OWNER.md:40-42`).

**Negative impact.** A stale bundle can continue to win indefinitely if it still applies chosen names; the owner sees no red state or forced refresh. Conversely, because age is excluded from the shadow declaration, changing the age cap itself does not invalidate a prepared dependency packet. This is intentional, but weakens stale-state detection and makes “60 days” look like a guarantee it is not.

**Likelihood / severity / confidence.** High likelihood over a quiet provider; **MEDIUM** maintenance/staleness severity, high confidence.

**Cheaper/safer alternative.** Keep age advisory but surface `past_age_cap` in status/Needs you and require explicit owner acknowledgement before a stale provider remains primary for another packet. Do not fail a working build automatically.

**SAFE-NOW mitigation.** Include age/cap in the resolver's structured observation and status card as a warning only; add a contract test that proves it never changes the winner. This preserves the owner decision. Owner approval is needed for any acknowledgement workflow.

### M2 — Watched providers are suppressed until they reach the current app version, so useful patches can be invisible indefinitely

**What / where.** All 10 watch rows are in `src/patches/DECISIONS.json:804-933`: Photos De-Vanced, Truecaller oyasumi, Facebook andrewliang25/Froggo, Instagram kveld9, Hotstar paresh, MX MightyMichs, and Telegram mich111discord/stylus/rahul9999xda. Eight dropped-provider rows are at `:935-986` (Instagram Foxxo/piko-lite/dawidd/Dreaming/giaaaacomo; Reddit Santodan/Mubelotix; Telegram newuser7171). Needs you suppresses dropped providers and suppresses watched rows until `newest >= ours` (`src/etc/needs_you.py:464-472`).

**Negative impact.** The owner may never see a watched provider's useful patch when it supports an older app, even if that patch is independently valuable or is the only fallback for a broken current provider. A drop is irreversible to normal discovery: `decisions.provider_state` returns `drop` before `watch` (`src/etc/decisions.py:44-53`), and Needs you `continue`s it. W16x has concrete stale gaps: Facebook watched providers list 573/577 while ours is 584; Instagram 447 vs 452; Hotstar 26.04 vs ours 26.06; MX 2.2.4 vs ours 1.93.4 (`DECISIONS.json:829-904`).

**Likelihood / severity / confidence.** High likelihood for these already-stale rows; **MEDIUM** opportunity/maintenance severity, high confidence.

**Cheaper/safer alternative.** Keep the decision memory but show one low-noise monthly “watched below current version” digest with patch names and compatibility caveat. Do not adopt automatically.

**SAFE-NOW mitigation.** Change `needs_you.py:464-472` to retain one collapsed FYI row per watched provider (still no take/adopt action), and add a test that `drop` remains suppressed. This is safe with the owner decision, but needs an owner-approved UI/report wording change.

### M3 — “Switchable stays / always-on drops” relies on incomplete or non-enforced audit evidence

**What / where.** The owner rule is recorded in `docs/review/KT-2026-10-28.md:43` and the 660-row switch audit is `docs/review/SWITCH-AUDIT-2026-10-28.jsonl`. The owner dropped always-on content hides such as Instagram `Hide Instants`, `Hide all stories`, `Hide explore feed`, `Hide feed content`, `Hide Reels save button`, `Hide navigation buttons` (`DECISIONS.json:124-163`; onboarding corroborates at `docs/review/onboarding/instagram.md:211-212`) and Reddit's always-on adobo hides (`:166-241`). But many standing rows, including W16 additions and several takes, have no matching audit record; the audit itself has `default=unknown` for 101 rows and `switch=n/a` for 160 rows (computed from all 660 JSONL rows). There is no code path that reads `SWITCH-AUDIT-2026-10-28.jsonl`; `selection_watch.py:456-470` applies the ledger verdict and the adoption policy, not switch evidence.

**Negative impact.** A wrong or unknown switch classification can either remove a desired feature permanently (drop) or ship an unwanted always-on content hide (take). `DECISIONS.json` also contains duplicate normalized decisions such as `AR Effects Slimmer` and `Clone app`; `decisions.call` takes the first matching row (`src/etc/decisions.py:35-41`), so later contradictory rows are not rejected by this helper. The selection writer does enforce BANNED and duplicate cross-bundle names (`src/etc/selection_writer.py:51-71,78-90`), but not switchability.

**Likelihood / severity / confidence.** Medium likelihood; **MEDIUM** user/maintenance severity, high confidence that the audit is documentation-only and has unknown rows. A specific misclassification is not proven here.

**Cheaper/safer alternative.** Make every future take/drop row carry a machine-checkable switch-audit reference and reject contradictory duplicate normalized rows. Keep the owner's switchable/always-on policy.

**SAFE-NOW mitigation.** Add a Validate contract that parses `DECISIONS.json`, normalizes names with `decisions.norm`, rejects conflicting `(target,norm(name))` calls, and requires a matching audit row for content-verbs; do not auto-change include/exclude files. This catches future mistakes without changing current decisions. Owner needed to resolve existing unknowns/duplicates.

### M4 — Keeping releases/tags this week increases storage, inventory work and stale-state risk

**What / where.** The owner explicitly said no cleanup apply until they say so (`docs/review/KT-2026-10-28.md:11`); W16w kept releases/tags and only cleaned LinkedIn (`docs/review/KT-2026-10-28.md:59-62`). Cleanup otherwise keeps one newest release/app, orphan build tags, and only five Pages deployment records (`src/etc/cleanup.py:7-24,35-40,160-205`). Release history reads up to 20 pages of 100 and returns `None` if incomplete (`src/build/release_notes.py:130-155`); status warns after more than 500 releases (`src/etc/status.py:323-336`).

**Negative impact.** GitHub release assets and tags consume storage/bandwidth and increase every inventory scan. More importantly, a high-version old release can keep `publish_guard` refusing a newer fallback/primary even if that release is no longer the desired shelf state. Cleanup deferral preserves rollback evidence, but it also preserves obsolete phone-facing records and the one-way version door. The W16x cleanup record shows the scale of prior local evidence deletion (875.60 MiB + 1,484.13 MiB), but does not measure GitHub release assets; no live release count was available in this lane.

**Likelihood / severity / confidence.** High likelihood of incremental cost; **MEDIUM** maintenance/storage severity, medium confidence for exact cost (unverified live asset totals), high confidence for bounded inventory behavior.

**Cheaper/safer alternative.** Keep one newest release per app plus a small, owner-approved evidence archive/receipt; delete old tags/releases only from a fresh tokenized preview. Preserve source commits and receipts, not APK bytes.

**SAFE-NOW mitigation.** None without changing the owner's “keep this week” decision. Run `cleanup.py preview` only (no apply), report counts/asset bytes, and defer deletion until owner confirms. Current cleanup already has token/re-read safeguards (`src/etc/cleanup.py:20-25`).

### M5 — Council “two models per seat” keeps known-stale IDs and spends calls before fallback

**What / where.** D16 keeps the nemotron seat listed and requires two models per seat, with a missing model falling through (`docs/review/KT-2026-10-28.md:61`). Current model arrays include two nemotron IDs and multiple provider IDs (`src/council/seats.json:93-126,245-317`); the policy says missing/busy own models fall through to backups (`src/council/seats.json:401`; `src/council/council.py:869-933`). The repo does not contain a fresh live catalogue proof for every current ID; the setup history records retired/missing model problems and quota/busy failures (`docs/council/SETUP.md:44-68`).

**Negative impact.** A stale first model costs a failed request/timeout before the second model or backup; if keys/backups are absent, the seat becomes `UNAVAILABLE` and quorum can be lost (`src/council/council.py:929-942`, quorum 3 in `src/council/seats.json:3`). “Keep two” prevents an empty-looking seat but can mask that both IDs are unavailable; live catalogue changes are outside CI's deterministic gates.

**Likelihood / severity / confidence.** Medium likelihood; **MEDIUM** review-coverage/quota severity, medium confidence because current provider availability was not live-verified here. The fallback code itself is verified.

**Cheaper/safer alternative.** Keep two entries for resilience, but replace a model only after the scheduled probe shows `SERVED`; use the proven alternate and retain the old ID only in probe history.

**SAFE-NOW mitigation.** Add a deterministic config lint requiring two models *and* a recent recorded served-probe timestamp/model per seat; do not silently replace IDs. Owner must choose a live NVIDIA replacement for nemotron (as D16 says).

### L1 — Permanent drops can suppress future compatible fixes/features

**What / where.** `DECISIONS.json` defines `drop` as “never adopted, never asked again” (`src/patches/DECISIONS.json:1-2`), and `decisions.call` turns future matching names into `skip` (`src/etc/selection_watch.py:456-468`). The rows cover all target groups: Truecaller (lines 5-31), Instagram (117-163,713-750), Reddit (166-241), Facebook (278-289,601-604,741-744), MX/ES/AdGuard/Prime/Photos/Hotstar/Telegram/LinkedIn (292-451,491-799). Many are security/identity safeguards (certificate, signature, clone, spoof, MicroG, proxy/VPN) and are appropriately vetoed by `BANNED`/`CONFIRM` (`src/patches/BANNED:1-21`, `CONFIRM:1-24`); the negative is that benign UI/features sharing a normalized future name are also suppressed.

**Likelihood / severity / confidence.** Low-to-medium name-collision likelihood; **LOW/MEDIUM** feature opportunity cost; high confidence in one-way skip behavior.

**Cheaper/safer alternative.** Time-bound drops (reconsider after provider/app major-version change) rather than “never ask again,” while retaining hard BANNED/CONFIRM enforcement.

**SAFE-NOW mitigation.** None without changing the owner’s drop semantics. A periodic owner-only report of dropped names newly offered at a materially newer app version would reduce lock-in without adopting; owner approval needed.

## Complete decision ledger coverage

The following lists cover every current owner decision row; grouped rows share the same negative mechanism above. The exact rows are in `src/patches/DECISIONS.json` at the cited ranges.

- **Take rows:** Truecaller `Hide business media`, `Stop call history sync`, `Hide frequently called contacts`, `Hide important senders` (`:12-17,482-487,776-787`); Instagram 14 names (`:33-115,608-620`); Reddit seven cosmetic/search names (`:187-259`); Facebook 18 feed/ads/AI/download/theme/icon names (`:264-276,496-597,755-759`); MX `Hide top tiles`, `Unlock MX Player Pro` (`:292-297,678-682`); Photos `AMOLED dark theme`, `Fix selected account persistence` (`:383-389,475-479`); Hotstar codecs/mirroring/screenshots/HDR10/ads (`:629-661`); Telegram Premium/font (`:685-697`); Amazon Music three paid names (`:454-472`); CCleaner Premium (`:762-766`). These are exposed to future normalized-name auto-adoption by `selection_watch.py:456-470`; paid Amazon is the H2 exception.
- **Drop rows:** Truecaller (`:5-31,489-494`); Instagram UI/content/identity/debug/signature/clone rows (`:117-163,713-751`); Reddit (`:166-185,208-241`); Facebook signature/launch/clone (`:278-289,601-604,741-744`); MX (`:299-317`); ES File (`:320-359`); AdGuard/Prime (`:362-380`); Photos identity/DRM/branding (`:391-403,699-710`); Hotstar security/identity/TV/premium/signature (`:405-445,664-675`); Telegram MicroG (`:447-451`); CCleaner telemetry (`:769-773`); LinkedIn GmsCore/gaps (`:790-802`). Most safety rows are reinforced by `BANNED`/`CONFIRM`; benign UI drops carry the L1 future-feature cost.
- **Watch rows:** Photos De-Vanced; Truecaller oyasumi; Facebook andrewliang25/Froggo; Instagram kveld9; Hotstar paresh; MX MightyMichs; Telegram MightyMichs/stylus/rahul (`:804-933`). Watch hides until supported version (`needs_you.py:464-472`), producing M2 and idle fallback work (H4).
- **Drop-provider rows:** Instagram Foxxo, piko-lite, dawidd612, Dreaming-Codes, giaaaacomo; Reddit Santodan/Mubelotix; Telegram newuser7171 (`:935-986`). `decisions.provider_state` makes drop precedence over watch (`decisions.py:44-53`), and `needs_you.py:464-468` permanently suppresses them; this is the provider-level form of L1. The Telegram row explicitly records it never built on 12.10.4 (`DECISIONS.json:955-960`), so its evidence is stronger than the rows with no “why.”

## Owner questions

- **Question:** Should pinned targets run a daily exact store-file health check even when no provider release changed? **Recommended:** yes, read-only missing/unknown alert; downside: extra store traffic and occasional false alarms, versus leaving a removed pin stale and silent.
- **Question:** Should Amazon Music remain in `paid_ok_targets` after the throwaway account ban? **Recommended:** no for automatic adoption; retain only a manual throwaway test exception; downside: fewer premium patches and owner review work, versus repeated account bans.
- **Question:** Should the Android 10 distribution remain signer-unpinned? **Recommended:** temporarily, only with an out-of-band signer/SHA check while filing the Obtainium fix; downside: manual burden and possible blocked updates, versus accepting unauthenticated first downloads.
- **Question:** Should an ineligible fallback (no exact target version) be smoke-tested? **Recommended:** no automatic smoke; record it as watched/idle until exact support; downside: less early warning, versus repeated red minutes and misleading status.
- **Question:** Is `pf_near_version_safe`'s same-first-two-components rule acceptable? **Recommended:** require per-target version-family or qualified exact/build-code evidence before widening it; downside: more refusals and owner admissions, versus a semantic downgrade hidden as a near version.
- **Question:** Should `max_patch_age_days` remain advisory? **Recommended:** yes, but surface an explicit stale-provider FYI/acknowledgement; downside: added report noise, versus a stale bundle looking guaranteed fresh.
- **Question:** Should watched providers be shown below the current version? **Recommended:** yes, one collapsed monthly digest, never auto-adopt; downside: a small amount of owner reading, versus permanently invisible alternatives.
- **Question:** Should release/tag cleanup be applied now? **Recommended:** owner-approved preview first, then keep one newest app release plus receipts; downside: less rollback/download history, versus storage and version-door growth.
- **Question:** Should each Council seat retain two model IDs even when one is missing? **Recommended:** retain two only with a recent served-probe record and replace stale IDs after D16 owner approval; downside: temporary seat reduction during replacement, versus wasted calls/quorum loss hidden by stale entries.
- **Question:** Should unknown/duplicate switch-audit rows block future decision PRs? **Recommended:** yes for content-verbs and contradictory normalized names; downside: slower adoption until evidence is filled, versus shipping an always-on hide or dropping a switchable feature.

## Limitations

- No live GitHub release inventory or live provider/model catalogue was queried in this lane; exact current asset-storage totals and current Council availability remain unverified. The report uses immutable/local records and owner-run evidence.
- H5's false-refusal/broad-acceptance cases are code-level risks; W16x records correct Amazon refusal and accepted Prime/Hotstar near-version cases, but no concrete false refusal.
- The Amazon account-ban event is an owner-recorded observation; this lane did not independently reproduce a ban.

CHANGES: none (read-only review)
FINDINGS: H=5 M=5 L=1
